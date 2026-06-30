from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


TraceStatus = Literal["started", "succeeded", "failed", "info"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_trace_event(
    name: str,
    status: TraceStatus = "info",
    details: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    return {
        "trace_id": f"trace-{uuid4().hex}",
        "name": name,
        "status": status,
        "details": details or {},
        "error_message": error_message,
        "created_at": utc_now_iso(),
    }


def append_trace_event(
    trace: list[dict[str, Any]],
    name: str,
    status: TraceStatus = "info",
    details: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    event = make_trace_event(
        name=name,
        status=status,
        details=details,
        error_message=error_message,
    )
    trace.append(event)
    return event
