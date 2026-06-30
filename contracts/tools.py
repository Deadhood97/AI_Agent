from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .base import ContractModel


class ToolCallRecord(ContractModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: Literal["succeeded", "failed"]
    result: Any = None
    error_message: str | None = None

