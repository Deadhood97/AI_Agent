from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from contracts import ConversationTurn, DatasetMetadata, ResolvedIntent
from contracts.briefing import DatasetBriefing, SuggestedQuestion
from contracts.analysis import AnalysisExecutionResult
from core.artifacts import ArtifactStore, dataset_id_for
from core.answers import format_analysis_answer
from core.csv_io import read_csv_bytes
from core.dataframe_context import build_dataframe_context, build_tool_context_payload
from core.dataset_tools import DatasetTools
from core.dataset_metadata import build_dataset_metadata
from core.execution import execute_dataframe_code, validate_generated_code
from core.langsmith_tracing import (
    compact_metadata_for_langsmith,
    langsmith_span,
    summarize_code_for_langsmith,
    summarize_output_for_langsmith,
    summarize_plan_for_langsmith,
    summarize_suggestions_for_langsmith,
    summarize_trace_events_for_langsmith,
    tracing_status,
)
from core.llm_planner import LLM_PLANNER_VERSION, LLMPlannerUnavailable, llm_plan_question
from core.memory import MemoryStore, build_memory_context
from core.planning import PlanningError, deterministic_plan, plan_question
from core.question_suggestions import suggest_questions
from core.serialization import serialize_analysis_outputs
from core.sessions import attach_turn_to_session, create_dataset_session, load_session, load_turn, new_turn_id
from core.simple_planner import SimplePlanError, plan_simple_question
from core.tracing import append_trace_event
from ui.cli_app import main as cli_main
from evals.langsmith_smoke import expected_output_evaluator, execution_succeeded_evaluator, target


class FoundationTests(unittest.TestCase):
    def test_csv_ingestion_reads_simple_csv(self):
        df, parser = read_csv_bytes(b"name,value\nA,1\nB,2\n")
        self.assertEqual(parser, "default pandas C parser")
        self.assertEqual(df["value"].sum(), 3)

    def test_dataset_metadata_validates_against_contract(self):
        df = pd.DataFrame({"name": ["A", "B"], "value": [1, 2]})
        metadata = build_dataset_metadata(df, "sample.csv", b"name,value\nA,1\nB,2\n", "demo")
        validated = DatasetMetadata.model_validate(metadata)
        self.assertEqual(validated.row_count, 2)
        self.assertEqual(validated.columns[1].inferred_role, "numeric")
        self.assertIn("Dataset context JSON", build_dataframe_context(metadata, df))

    def test_safe_execution_returns_analysis_outputs(self):
        df = pd.DataFrame({"value": [1, 2, 3]})
        outputs = execute_dataframe_code(df, "analysis_outputs = {'total': int(df['value'].sum())}")
        self.assertEqual(outputs["total"], 6)
        serialized = serialize_analysis_outputs(outputs)
        self.assertEqual(serialized["total"]["kind"], "scalar")

    def test_unsafe_code_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "import"):
            validate_generated_code("import os\nanalysis_outputs = {}")
        with self.assertRaisesRegex(ValueError, "open"):
            validate_generated_code("analysis_outputs = {'x': open('secret.txt')}")

    def test_artifact_store_writes_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ArtifactStore(Path(temp_dir))
            metadata = {"source_file": "sample.csv", "file_sha256": "abcdef1234567890"}
            dataset_id = dataset_id_for(metadata)
            path = store.write_json("metadata", dataset_id, metadata)
            self.assertTrue(path.exists())
            self.assertEqual(store.read_json("metadata", dataset_id)["source_file"], "sample.csv")

    def test_conversation_turn_contract(self):
        turn = ConversationTurn.model_validate(
            {
                "turn_id": "turn-1",
                "session_id": "session-1",
                "user_message": "What is the total?",
                "resolved_intent": ResolvedIntent().model_dump(),
                "assistant_answer": "The total is 6.",
                "created_at": "2026-05-31T00:00:00Z",
            }
        )
        self.assertEqual(turn.resolved_intent.question_type, "analysis")

    def test_dataframe_tool_context_payload_is_json_safe(self):
        df = pd.DataFrame({"name": ["A", "B"], "value": [1.5, None]})
        metadata = build_dataset_metadata(df, "sample.csv", b"name,value\nA,1.5\nB,\n")
        payload = build_tool_context_payload(metadata, df, rows=2)
        self.assertEqual(payload["metadata"]["source_file"], "sample.csv")
        self.assertEqual(payload["preview_rows"][1]["value"], None)

    def test_session_and_turn_artifacts_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ArtifactStore(Path(temp_dir))
            df = pd.DataFrame({"name": ["A"], "value": [1]})
            metadata = build_dataset_metadata(df, "sample.csv", b"name,value\nA,1\n")
            dataset_id = dataset_id_for(metadata)
            session = create_dataset_session(dataset_id, metadata, store=store)
            turn = ConversationTurn.model_validate(
                {
                    "turn_id": new_turn_id(),
                    "session_id": session.session_id,
                    "user_message": "What is the total?",
                    "resolved_intent": ResolvedIntent().model_dump(),
                    "assistant_answer": "The total is 1.",
                    "created_at": session.created_at,
                }
            )
            updated = attach_turn_to_session(session, turn, store=store)

            self.assertEqual(load_session(store, session.session_id).turn_ids, [turn.turn_id])
            self.assertEqual(load_turn(store, turn.turn_id).assistant_answer, "The total is 1.")
            self.assertGreaterEqual(updated.updated_at, session.updated_at)

    def test_memory_records_can_be_rendered_for_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryStore(ArtifactStore(Path(temp_dir)))
            record = memory.add(
                session_id="session-1",
                turn_id="turn-1",
                memory_type="analytical",
                summary="Calculated total revenue by region.",
                artifact_ids=["output-1"],
            )

            records = memory.recent_for_session("session-1")
            context = build_memory_context(records)
            self.assertEqual(records[0].memory_id, record.memory_id)
            self.assertIn("Calculated total revenue by region.", context)
            self.assertIn("output-1", context)

    def test_trace_event_appends_status_and_details(self):
        trace: list[dict] = []
        event = append_trace_event(trace, "execute_code", "succeeded", {"rows": 3})
        self.assertEqual(trace, [event])
        self.assertEqual(event["details"]["rows"], 3)

    def test_dataset_tools_ingest_and_analysis_turn(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools = DatasetTools(ArtifactStore(Path(temp_dir)))
            result = tools.ingest_csv_bytes(
                b"region,revenue\nEast,10\nWest,20\n",
                "sales.csv",
                "demo sales",
            )
            preview = tools.preview_for_session(result.session_id, rows=1)
            turn = tools.run_analysis_turn(
                result.session_id,
                "What is total revenue?",
                "analysis_outputs = {'total_revenue': int(df['revenue'].sum())}",
            )

            self.assertEqual(result.metadata.row_count, 2)
            self.assertIn("build_dataset_metadata", [event["name"] for event in result.trace])
            self.assertIn("suggest_questions", [event["name"] for event in result.trace])
            self.assertEqual(preview["preview_rows"][0]["region"], "East")
            self.assertEqual(turn.execution_result.status, "succeeded")
            self.assertEqual(turn.execution_result.serialized_output.value, 30)
            self.assertIn("30", turn.assistant_answer)

    def test_dataset_tools_records_failed_analysis_turn(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools = DatasetTools(ArtifactStore(Path(temp_dir)))
            result = tools.ingest_csv_bytes(b"x\n1\n", "sample.csv")
            turn = tools.run_analysis_turn(
                result.session_id,
                "Try unsafe code",
                "import os\nanalysis_outputs = {}",
            )

            self.assertEqual(turn.execution_result.status, "failed")
            self.assertEqual(turn.execution_result.error_type, "ValueError")
            self.assertIn("import", turn.execution_result.error_message)
            self.assertIn("could not compute", turn.assistant_answer)

    def test_answer_formatter_handles_table_and_failure_results(self):
        table_answer = format_analysis_answer(
            AnalysisExecutionResult.model_validate(
                {
                    "status": "succeeded",
                    "output_key": "by_region",
                    "serialized_output": {
                        "kind": "table",
                        "type": "DataFrame",
                        "columns": ["region", "revenue"],
                        "rows": [{"region": "East", "revenue": 10}],
                        "row_count": 1,
                    },
                }
            )
        )
        failed_answer = format_analysis_answer(
            AnalysisExecutionResult.model_validate(
                {
                    "status": "failed",
                    "error_type": "ValueError",
                    "error_message": "Generated code may not import modules.",
                }
            )
        )

        self.assertIn("Computed table result", table_answer)
        self.assertIn("East", table_answer)
        self.assertIn("could not compute", failed_answer)

    def test_simple_planner_handles_common_questions(self):
        df = pd.DataFrame({"region": ["East", "West"], "revenue": [10, 20]})
        metadata = build_dataset_metadata(df, "sales.csv", b"region,revenue\nEast,10\nWest,20\n")

        row_count = plan_simple_question("How many rows are there?", metadata)
        total = plan_simple_question("What is the total revenue?", metadata)
        grouped = plan_simple_question("Count by region", metadata)

        self.assertIn("len(df)", row_count.code)
        self.assertIn("sum", total.code)
        self.assertEqual(total.resolved_intent.metrics, ["sum:revenue"])
        self.assertIn("count_by_region", grouped.code)
        self.assertEqual(grouped.resolved_intent.grouping, ["region"])

        with self.assertRaises(SimplePlanError):
            plan_simple_question("Why did revenue change?", metadata)

    def test_question_suggestions_use_dataset_metadata(self):
        df = pd.DataFrame({"region": ["East", "West"], "revenue": [10, 20]})
        metadata = build_dataset_metadata(df, "sales.csv", b"region,revenue\nEast,10\nWest,20\n")

        suggestions = suggest_questions(metadata)

        self.assertEqual(len(suggestions), 3)
        self.assertIsInstance(suggestions[0], SuggestedQuestion)
        self.assertEqual(suggestions[0].question, "What is the total revenue?")
        self.assertEqual(suggestions[1].question, "Count by region")
        self.assertEqual(suggestions[2].question, "What is the average revenue?")
        self.assertEqual(suggestions[0].columns, ["revenue"])
        self.assertEqual(suggestions[1].expected_visualization, "bar")

    def test_deterministic_planner_returns_explainable_plan_contract(self):
        df = pd.DataFrame({"region": ["East", "West"], "revenue": [10, 20]})
        metadata = build_dataset_metadata(df, "sales.csv", b"region,revenue\nEast,10\nWest,20\n")

        plan = deterministic_plan("What is the total revenue?", metadata)
        planning_result = plan_question("What is the total revenue?", metadata)
        summary = summarize_plan_for_langsmith(plan)

        self.assertEqual(plan.planner, "deterministic")
        self.assertEqual(plan.resolved_intent.metrics, ["sum:revenue"])
        self.assertEqual(plan.columns_needed, ["revenue"])
        self.assertIn("analysis_outputs", plan.code)
        self.assertEqual(planning_result.selected_plan.code, plan.code)
        self.assertEqual(planning_result.attempts[0].status, "succeeded")
        self.assertEqual(summary["metrics"], ["sum:revenue"])

    def test_planning_error_explains_when_no_planner_can_handle_question(self):
        df = pd.DataFrame({"region": ["East", "West"], "revenue": [10, 20]})
        metadata = build_dataset_metadata(df, "sales.csv", b"region,revenue\nEast,10\nWest,20\n")

        with self.assertRaisesRegex(PlanningError, "deterministic: failed"):
            plan_question("Why did revenue change?", metadata)

    def test_llm_planner_reports_missing_key_clearly(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            with self.assertRaisesRegex(LLMPlannerUnavailable, "OPENAI_API_KEY"):
                llm_plan_question("Why did revenue change?", {"columns": []})

    def test_plan_question_can_fallback_to_llm_when_enabled(self):
        df = pd.DataFrame({"region": ["East", "West"], "revenue": [10, 20]})
        metadata = build_dataset_metadata(df, "sales.csv", b"region,revenue\nEast,10\nWest,20\n")
        llm_plan = deterministic_plan("What is the total revenue?", metadata).model_copy(
            update={
                "question": "Which region has the highest revenue?",
                "planner": "llm",
                "planner_version": LLM_PLANNER_VERSION,
                "code": (
                    "_ranked = df.groupby('region', as_index=False)['revenue'].sum()"
                    ".sort_values('revenue', ascending=False)\n"
                    "analysis_outputs = {'top_region_by_revenue': _ranked.head(1)}"
                ),
                "columns_needed": ["region", "revenue"],
                "metrics": ["sum:revenue"],
                "grouping": ["region"],
                "rationale": "Find the grouped revenue leader.",
                "confidence": 0.72,
            }
        )

        with patch("core.llm_planner.llm_plan_question", return_value=llm_plan):
            result = plan_question("Which region has the highest revenue?", metadata, allow_llm=True)

        self.assertEqual(result.attempts[0].planner, "deterministic")
        self.assertEqual(result.attempts[0].status, "failed")
        self.assertEqual(result.attempts[1].planner, "llm")
        self.assertEqual(result.attempts[1].status, "succeeded")
        self.assertEqual(result.selected_plan.planner, "llm")

    def test_dataset_tools_can_run_planned_turn(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools = DatasetTools(ArtifactStore(Path(temp_dir)))
            result = tools.ingest_csv_bytes(
                b"region,revenue\nEast,10\nWest,20\n",
                "sales.csv",
            )
            turn = tools.run_planned_turn(result.session_id, "What is the total revenue?")

            self.assertEqual(turn.execution_result.status, "succeeded")
            self.assertEqual(turn.execution_result.serialized_output.value, 30.0)
            self.assertEqual(turn.resolved_intent.metrics, ["sum:revenue"])
            self.assertEqual(turn.analysis_plan.planner, "deterministic")
            self.assertTrue((Path(temp_dir) / "plans" / f"{result.session_id}-deterministic.json").exists())

    def test_dataset_tools_persist_suggested_questions_on_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools = DatasetTools(ArtifactStore(Path(temp_dir)))
            result = tools.ingest_csv_bytes(
                b"region,revenue\nEast,10\nWest,20\n",
                "sales.csv",
            )

            session = load_session(tools.artifact_store, result.session_id)
            suggestions = tools.suggest_questions_for_session(result.session_id)

            self.assertIsInstance(result.dataset_briefing, DatasetBriefing)
            self.assertIn("sales.csv", result.dataset_briefing.summary)
            self.assertEqual(session.dataset_briefing.key_metrics, ["revenue"])
            self.assertEqual(result.suggested_questions[0].question, "What is the total revenue?")
            self.assertEqual(session.suggested_questions[0]["question"], "What is the total revenue?")
            self.assertEqual(suggestions[1].question, "Count by region")

    def test_dataset_tools_attaches_chart_payload_for_grouped_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools = DatasetTools(ArtifactStore(Path(temp_dir)))
            result = tools.ingest_csv_bytes(
                b"region,revenue\nEast,10\nWest,20\nEast,5\n",
                "sales.csv",
            )
            turn = tools.run_planned_turn(result.session_id, "Count by region")

            self.assertIsNotNone(turn.chart_payload)
            self.assertEqual(turn.chart_payload.chart_type, "bar")
            self.assertEqual(turn.chart_payload.x, "region")
            self.assertEqual(turn.chart_payload.y, "count")
            self.assertTrue((Path(temp_dir) / "charts" / f"{turn.chart_payload.chart_id}.json").exists())

    def test_cli_can_show_suggestions_without_question(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "sales.csv"
            csv_path.write_text("region,revenue\nEast,10\nWest,20\n", encoding="utf-8")

            with patch("builtins.print") as mocked_print:
                exit_code = cli_main([str(csv_path), "--artifacts", str(Path(temp_dir) / "artifacts")])

            printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list)
            self.assertEqual(exit_code, 0)
            self.assertIn("Suggested questions:", printed)
            self.assertIn("What is the total revenue?", printed)
            self.assertIn("Count by region", printed)

    def test_langsmith_span_noops_when_disabled(self):
        with patch.dict("os.environ", {"LANGSMITH_TRACING": "false"}, clear=False):
            with langsmith_span("disabled-test") as span:
                self.assertIsNone(span)
            self.assertFalse(tracing_status()["enabled"])

    def test_langsmith_metadata_payload_omits_full_column_samples(self):
        df = pd.DataFrame({"region": ["East", "West"], "revenue": [10, 20]})
        metadata = build_dataset_metadata(df, "sales.csv", b"region,revenue\nEast,10\nWest,20\n")
        payload = compact_metadata_for_langsmith(metadata)

        self.assertEqual(payload["source_file"], "sales.csv")
        self.assertEqual(payload["columns"][0]["name"], "region")
        self.assertNotIn("sample_values", payload["columns"][0])
        self.assertNotIn("top_values", payload["columns"][0])

    def test_langsmith_suggestion_and_trace_summaries_are_compact(self):
        df = pd.DataFrame({"region": ["East", "West"], "revenue": [10, 20]})
        metadata = build_dataset_metadata(df, "sales.csv", b"region,revenue\nEast,10\nWest,20\n")
        suggestions = suggest_questions(metadata)
        trace = [
            append_trace_event([], "read_csv", "succeeded", {"rows": 2}),
        ]

        suggestion_summary = summarize_suggestions_for_langsmith(suggestions)
        trace_summary = summarize_trace_events_for_langsmith(trace)
        code_summary = summarize_code_for_langsmith("analysis_outputs = {'rows': len(df)}")

        self.assertEqual(suggestion_summary[0]["rank"], 1)
        self.assertEqual(suggestion_summary[0]["question"], "What is the total revenue?")
        self.assertEqual(trace_summary[0]["name"], "read_csv")
        self.assertNotIn("trace_id", trace_summary[0])
        self.assertTrue(code_summary["creates_analysis_outputs"])

    def test_langsmith_output_summary_omits_table_rows(self):
        output = {
            "kind": "table",
            "type": "DataFrame",
            "columns": ["region", "revenue"],
            "rows": [{"region": "East", "revenue": 10}],
            "row_count": 1,
            "truncated": False,
        }
        summary = summarize_output_for_langsmith(output)

        self.assertEqual(summary["preview_row_count"], 1)
        self.assertNotIn("rows", summary)

    def test_langsmith_eval_target_runs_local_pipeline(self):
        outputs = target(
            {
                "filename": "sales.csv",
                "csv_text": "region,revenue\nEast,10\nWest,20\n",
                "question": "What is the total revenue?",
            }
        )

        self.assertEqual(outputs["status"], "succeeded")
        self.assertEqual(outputs["output"]["kind"], "scalar")
        self.assertEqual(outputs["output"]["value"], 30.0)

    def test_langsmith_eval_evaluators_score_outputs(self):
        outputs = {
            "status": "succeeded",
            "output": {"kind": "scalar", "value": 30.0},
            "error_message": None,
        }
        success_score = execution_succeeded_evaluator({}, outputs, {})
        expected_score = expected_output_evaluator(
            {},
            outputs,
            {"expected_kind": "scalar", "expected_value": 30.0},
        )

        self.assertEqual(success_score["score"], 1)
        self.assertEqual(expected_score["score"], 1)


if __name__ == "__main__":
    unittest.main()
