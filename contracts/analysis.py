from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .base import ContractModel


class SerializedAnalysisOutput(ContractModel):
    kind: Literal["table", "mapping", "scalar"]
    type: str
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int | None = None
    truncated: bool = False
    value: Any = None


class AnalysisExecutionResult(ContractModel):
    status: Literal["succeeded", "failed"]
    output_key: str | None = None
    serialized_output: SerializedAnalysisOutput | None = None
    row_count: int | None = None
    columns: list[str] = Field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None
    repair_attempts: int = 0

