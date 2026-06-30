from __future__ import annotations

from typing import Any

from contracts import ChartPayload, ConversationTurn, ResolvedIntent
from contracts.analysis import AnalysisExecutionResult
from core.answers import format_analysis_answer
from core.artifacts import ArtifactStore
from core.charting import recommend_chart_payload
from core.dataset_sessions import DatasetSessionService
from core.execution import execute_dataframe_code
from core.langsmith_tracing import (
    compact_metadata_for_langsmith,
    end_langsmith_span,
    langsmith_span,
    summarize_code_for_langsmith,
    summarize_output_for_langsmith,
    summarize_plan_for_langsmith,
    summarize_trace_events_for_langsmith,
)
from core.planning import PlanningError, plan_question
from core.serialization import serialize_analysis_outputs
from core.sessions import attach_turn_to_session, new_turn_id
from core.tracing import append_trace_event, utc_now_iso


class AnalysisTurnService:
    def __init__(self, artifact_store: ArtifactStore, session_service: DatasetSessionService):
        self.artifact_store = artifact_store
        self.session_service = session_service

    def run_analysis_turn(
        self,
        session_id: str,
        user_message: str,
        code: str,
        output_key: str | None = None,
        resolved_intent: ResolvedIntent | dict | None = None,
        analysis_plan: dict[str, Any] | None = None,
    ) -> ConversationTurn:
        with langsmith_span(
            "DatasetTools.run_analysis_turn",
            run_type="chain",
            inputs={
                "session_id": session_id,
                "user_message": user_message,
                "output_key": output_key,
                "analysis_plan": summarize_plan_for_langsmith(analysis_plan),
            },
        ) as span:
            trace: list[dict[str, Any]] = []
            df, session = self.session_service.load_dataframe_for_session(session_id)
            intent = ResolvedIntent.model_validate(resolved_intent or {})
            append_trace_event(trace, "execute_dataframe_code", "started")

            execution_result: AnalysisExecutionResult
            try:
                with langsmith_span(
                    "execute_dataframe_code",
                    run_type="tool",
                    inputs={"session_id": session_id, "code": summarize_code_for_langsmith(code)},
                ) as execute_span:
                    outputs = execute_dataframe_code(df, code)
                    serialized_outputs = serialize_analysis_outputs(outputs)
                    selected_key = output_key or next(iter(serialized_outputs), None)
                    selected_output = serialized_outputs.get(selected_key) if selected_key else None
                    end_langsmith_span(
                        execute_span,
                        {
                            "output_key": selected_key,
                            "selected_output": summarize_output_for_langsmith(selected_output),
                        },
                    )
                if selected_key is not None:
                    self.artifact_store.write_json(
                        "analysis_outputs",
                        f"{session_id}-{selected_key}",
                        selected_output,
                    )
                execution_result = AnalysisExecutionResult.model_validate(
                    {
                        "status": "succeeded",
                        "output_key": selected_key,
                        "serialized_output": selected_output,
                        "row_count": selected_output.get("row_count") if selected_output else None,
                        "columns": selected_output.get("columns", []) if selected_output else [],
                    }
                )
                append_trace_event(trace, "execute_dataframe_code", "succeeded", {"output_key": selected_key})
            except Exception as exc:
                execution_result = AnalysisExecutionResult.model_validate(
                    {
                        "status": "failed",
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                )
                append_trace_event(
                    trace,
                    "execute_dataframe_code",
                    "failed",
                    error_message=str(exc),
                )

            with langsmith_span(
                "format_analysis_answer",
                run_type="parser",
                inputs={"status": execution_result.status, "output_key": execution_result.output_key},
            ) as answer_span:
                assistant_answer = format_analysis_answer(execution_result)
                end_langsmith_span(answer_span, {"answer": assistant_answer})

            chart_payload: ChartPayload | None = recommend_chart_payload(
                execution_result.output_key,
                execution_result.serialized_output,
                intent,
            )
            if chart_payload is not None:
                self.artifact_store.write_json("charts", chart_payload.chart_id, chart_payload.model_dump())
                append_trace_event(
                    trace,
                    "recommend_chart_payload",
                    "succeeded",
                    {"chart_id": chart_payload.chart_id, "chart_type": chart_payload.chart_type},
                )

            turn = ConversationTurn.model_validate(
                {
                    "turn_id": new_turn_id(),
                    "session_id": session_id,
                    "user_message": user_message,
                    "resolved_intent": intent.model_dump(),
                    "generated_code": code,
                    "analysis_plan": analysis_plan,
                    "execution_result": execution_result.model_dump(),
                    "chart_payload": chart_payload.model_dump() if chart_payload else None,
                    "assistant_answer": assistant_answer,
                    "trace": trace,
                    "created_at": utc_now_iso(),
                }
            )
            attach_turn_to_session(session, turn, store=self.artifact_store)
            self.artifact_store.write_json("traces", turn.turn_id, trace)
            end_langsmith_span(
                span,
                {
                    "turn_id": turn.turn_id,
                    "status": execution_result.status,
                    "output_key": execution_result.output_key,
                    "trace_events": summarize_trace_events_for_langsmith(trace),
                    "generated_code": summarize_code_for_langsmith(code),
                    "selected_output": summarize_output_for_langsmith(
                        execution_result.serialized_output.model_dump()
                        if execution_result.serialized_output
                        else None
                    ),
                },
            )
            return turn

    def run_planned_turn(self, session_id: str, user_message: str, allow_llm: bool = False) -> ConversationTurn:
        with langsmith_span(
            "DatasetTools.run_planned_turn",
            run_type="chain",
            inputs={"session_id": session_id, "user_message": user_message, "allow_llm": allow_llm},
        ) as span:
            _df, session = self.session_service.load_dataframe_for_session(session_id)
            with langsmith_span(
                "plan_question",
                run_type="tool",
                inputs={
                    "question": user_message,
                    "metadata": compact_metadata_for_langsmith(session.metadata.model_dump()),
                },
            ) as plan_span:
                try:
                    planning_result = plan_question(user_message, session.metadata.model_dump(), allow_llm=allow_llm)
                except PlanningError as exc:
                    end_langsmith_span(
                        plan_span,
                        {
                            "status": "failed",
                            "attempts": [attempt.model_dump(exclude={"plan"}) for attempt in exc.result.attempts],
                            "error_message": str(exc),
                        },
                    )
                    raise
                plan = planning_result.selected_plan
                end_langsmith_span(
                    plan_span,
                    {
                        "selected_plan": summarize_plan_for_langsmith(plan),
                        "attempts": [attempt.model_dump(exclude={"plan"}) for attempt in planning_result.attempts],
                    },
                )
            self.artifact_store.write_json("plans", f"{session_id}-{plan.planner}", plan.model_dump())
            turn = self.run_analysis_turn(
                session_id=session_id,
                user_message=user_message,
                code=plan.code,
                output_key=plan.output_key,
                resolved_intent=plan.resolved_intent,
                analysis_plan=plan.model_dump(),
            )
            end_langsmith_span(span, {"turn_id": turn.turn_id, "answer": turn.assistant_answer})
            return turn
