from __future__ import annotations

from contracts.planning import AnalysisPlan, PlanAttempt, PlanningResult
from core.simple_planner import SimplePlanError, plan_simple_question


DETERMINISTIC_PLANNER_VERSION = "simple-v1"


class PlanningError(ValueError):
    """Raised when no planner can produce an executable analysis plan."""

    def __init__(self, message: str, result: PlanningResult):
        super().__init__(message)
        self.result = result


def deterministic_plan(question: str, metadata: dict) -> AnalysisPlan:
    simple_plan = plan_simple_question(question, metadata)
    intent = simple_plan.resolved_intent
    columns_needed = list(dict.fromkeys([*intent.grouping, *[metric.split(":", 1)[-1] for metric in intent.metrics if ":" in metric]]))
    metrics = list(intent.metrics)
    grouping = list(intent.grouping)
    steps = [simple_plan.rationale, "Execute the generated pandas code against a dataframe copy."]

    return AnalysisPlan.model_validate(
        {
            "question": question,
            "planner": "deterministic",
            "planner_version": DETERMINISTIC_PLANNER_VERSION,
            "resolved_intent": intent.model_dump(),
            "code": simple_plan.code,
            "columns_needed": columns_needed,
            "metrics": metrics,
            "grouping": grouping,
            "filters": {str(key): str(value) for key, value in intent.filters.items()},
            "analysis_steps": steps,
            "rationale": simple_plan.rationale,
            "assumptions": ["The requested metric can be answered directly from the profiled columns."],
            "limitations": ["The deterministic planner only supports row counts, sums, means, and simple group counts."],
            "needs_clarification": intent.needs_clarification,
            "clarification_question": intent.clarification_question,
            "confidence": 0.9,
        }
    )


def plan_question(question: str, metadata: dict, allow_llm: bool = False) -> PlanningResult:
    attempts: list[PlanAttempt] = []
    try:
        plan = deterministic_plan(question, metadata)
        attempts.append(PlanAttempt(planner="deterministic", status="succeeded", plan=plan))
        return PlanningResult(question=question, selected_plan=plan, attempts=attempts)
    except SimplePlanError as exc:
        attempts.append(
            PlanAttempt(
                planner="deterministic",
                status="failed",
                reason="Question is outside deterministic planner coverage.",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        )

    if allow_llm:
        from core.llm_planner import llm_plan_question

        try:
            plan = llm_plan_question(question, metadata)
            attempts.append(PlanAttempt(planner="llm", status="succeeded", plan=plan))
            return PlanningResult(question=question, selected_plan=plan, attempts=attempts)
        except Exception as exc:
            attempts.append(
                PlanAttempt(
                    planner="llm",
                    status="failed",
                    reason="LLM planner could not produce a valid plan.",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )
    else:
        attempts.append(
            PlanAttempt(
                planner="llm",
                status="skipped",
                reason="LLM fallback is disabled for this call.",
            )
        )

    result = PlanningResult(question=question, selected_plan=None, attempts=attempts)
    raise PlanningError(_planning_error_message(result), result)


def _planning_error_message(result: PlanningResult) -> str:
    messages = [
        f"{attempt.planner}: {attempt.status}"
        + (f" - {attempt.error_message}" if attempt.error_message else f" - {attempt.reason}" if attempt.reason else "")
        for attempt in result.attempts
    ]
    return "No planner produced an executable plan. " + " | ".join(messages)
