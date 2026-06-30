from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator


TRUTHY_VALUES = {"1", "true", "yes", "on"}


def langsmith_enabled() -> bool:
    return os.getenv("LANGSMITH_TRACING", "").strip().lower() in TRUTHY_VALUES


def langsmith_available() -> bool:
    try:
        import langsmith  # noqa: F401
    except Exception:
        return False
    return True


def compact_metadata_for_langsmith(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_file": metadata.get("source_file"),
        "dataset_description_provided": bool(metadata.get("dataset_description")),
        "row_count": metadata.get("row_count"),
        "column_count": metadata.get("column_count"),
        "data_integrity": metadata.get("data_integrity", {}),
        "columns": [
            {
                "name": column.get("name"),
                "pandas_dtype": column.get("pandas_dtype"),
                "inferred_role": column.get("inferred_role"),
                "null_count": column.get("null_count"),
                "unique_count": column.get("unique_count"),
            }
            for column in metadata.get("columns", [])
        ],
    }


def summarize_suggestions_for_langsmith(suggestions: list[Any]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for index, suggestion in enumerate(suggestions, start=1):
        if hasattr(suggestion, "question"):
            summary.append(
                {
                    "rank": index,
                    "question": suggestion.question,
                    "question_type": suggestion.question_type,
                    "columns": list(suggestion.columns),
                    "rationale": suggestion.rationale,
                }
            )
        elif isinstance(suggestion, dict):
            summary.append(
                {
                    "rank": index,
                    "question": suggestion.get("question"),
                    "question_type": suggestion.get("question_type"),
                    "columns": suggestion.get("columns", []),
                    "rationale": suggestion.get("rationale"),
                }
            )
    return summary


def summarize_trace_events_for_langsmith(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": event.get("name"),
            "status": event.get("status"),
            "details": event.get("details", {}),
            "error_message": event.get("error_message"),
        }
        for event in trace
    ]


def summarize_code_for_langsmith(code: str) -> dict[str, Any]:
    stripped = code.strip()
    return {
        "code_chars": len(code),
        "code_lines": len(stripped.splitlines()) if stripped else 0,
        "creates_analysis_outputs": "analysis_outputs" in code,
    }


def summarize_plan_for_langsmith(plan: Any | None) -> dict[str, Any] | None:
    if plan is None:
        return None
    if hasattr(plan, "model_dump"):
        payload = plan.model_dump()
    elif isinstance(plan, dict):
        payload = plan
    else:
        return None
    return {
        "planner": payload.get("planner"),
        "planner_version": payload.get("planner_version"),
        "question": payload.get("question"),
        "columns_needed": payload.get("columns_needed", []),
        "metrics": payload.get("metrics", []),
        "grouping": payload.get("grouping", []),
        "needs_clarification": payload.get("needs_clarification", False),
        "confidence": payload.get("confidence"),
        "code": summarize_code_for_langsmith(str(payload.get("code") or "")),
        "rationale": payload.get("rationale"),
        "limitations": payload.get("limitations", []),
    }


def summarize_output_for_langsmith(output: dict[str, Any] | None) -> dict[str, Any] | None:
    if output is None:
        return None
    summary = {
        "kind": output.get("kind"),
        "type": output.get("type"),
        "row_count": output.get("row_count"),
        "columns": output.get("columns", []),
        "truncated": output.get("truncated", False),
    }
    if output.get("kind") in {"scalar", "mapping"}:
        summary["value"] = output.get("value")
    if output.get("kind") == "table":
        summary["preview_row_count"] = len(output.get("rows", [])[:5])
    return summary


@contextmanager
def langsmith_span(
    name: str,
    run_type: str = "chain",
    inputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[Any]:
    if not langsmith_enabled():
        yield None
        return

    try:
        import langsmith as ls
    except Exception:
        yield None
        return

    project_name = os.getenv("LANGSMITH_PROJECT") or None
    with ls.trace(
        name,
        run_type,
        project_name=project_name,
        inputs=inputs or {},
        metadata=metadata or {},
    ) as run_tree:
        yield run_tree


def end_langsmith_span(run_tree: Any, outputs: dict[str, Any] | None = None) -> None:
    if run_tree is None:
        return
    run_tree.end(outputs=outputs or {})


def tracing_status() -> dict[str, Any]:
    return {
        "enabled": langsmith_enabled(),
        "available": langsmith_available(),
        "project": os.getenv("LANGSMITH_PROJECT") or "default",
    }
