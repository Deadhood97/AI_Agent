from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field

from .analysis import AnalysisExecutionResult
from .base import ContractModel
from .charts import ChartPayload
from .tools import ToolCallRecord

if TYPE_CHECKING:
    from .planning import AnalysisPlan


class ResolvedIntent(ContractModel):
    question_type: str = "analysis"
    requires_code: bool = True
    requires_chart: bool = False
    filters: dict[str, Any] = Field(default_factory=dict)
    grouping: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    referenced_entities: list[str] = Field(default_factory=list)
    referenced_turn_ids: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None


class ConversationTurn(ContractModel):
    turn_id: str
    session_id: str
    user_message: str
    resolved_intent: ResolvedIntent
    referenced_turn_ids: list[str] = Field(default_factory=list)
    generated_code: str | None = None
    analysis_plan: AnalysisPlan | None = None
    execution_result: AnalysisExecutionResult | None = None
    chart_payload: ChartPayload | None = None
    assistant_answer: str = ""
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
