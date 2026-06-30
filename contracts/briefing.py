from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ContractModel


class SuggestedQuestion(ContractModel):
    question: str
    rationale: str
    question_type: Literal["summary", "analysis", "visualization", "quality", "follow_up"] = "analysis"
    columns: list[str] = Field(default_factory=list)
    priority: int = Field(default=3, ge=1, le=5)
    expected_visualization: str | None = None


class ColumnInsight(ContractModel):
    name: str
    role: str
    summary: str
    missing_percentage: float = 0
    unique_count: int | None = None
    warnings: list[str] = Field(default_factory=list)


class DatasetQualityWarning(ContractModel):
    severity: Literal["info", "warning", "critical"] = "info"
    message: str
    columns: list[str] = Field(default_factory=list)


class DatasetBriefing(ContractModel):
    summary: str
    row_count: int
    column_count: int
    generator: Literal["deterministic", "openai"] = "deterministic"
    model: str | None = None
    likely_subject: str = ""
    key_metrics: list[str] = Field(default_factory=list)
    key_dimensions: list[str] = Field(default_factory=list)
    time_fields: list[str] = Field(default_factory=list)
    column_insights: list[ColumnInsight] = Field(default_factory=list)
    quality_warnings: list[DatasetQualityWarning] = Field(default_factory=list)
    suggested_questions: list[SuggestedQuestion] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
