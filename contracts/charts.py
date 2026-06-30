from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ContractModel


class ChartPayload(ContractModel):
    chart_id: str
    chart_type: Literal["bar", "line", "scatter", "histogram", "table", "text", "kpi"]
    source_output_key: str
    title: str
    x: str | None = None
    y: str | None = None
    color: str | None = None
    top_n: int | None = None
    rationale: str = ""
    warnings: list[str] = Field(default_factory=list)

