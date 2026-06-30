from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ContractModel
from .turn import ResolvedIntent


class AnalysisPlan(ContractModel):
    question: str
    planner: Literal["deterministic", "llm"]
    planner_version: str
    resolved_intent: ResolvedIntent
    code: str
    output_key: str | None = None
    columns_needed: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    grouping: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
    analysis_steps: list[str] = Field(default_factory=list)
    rationale: str
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None
    confidence: float = Field(ge=0, le=1)


class PlanAttempt(ContractModel):
    planner: Literal["deterministic", "llm"]
    status: Literal["succeeded", "failed", "skipped"]
    reason: str = ""
    plan: AnalysisPlan | None = None
    error_type: str | None = None
    error_message: str | None = None


class PlanningResult(ContractModel):
    question: str
    selected_plan: AnalysisPlan | None = None
    attempts: list[PlanAttempt] = Field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return self.selected_plan is not None
