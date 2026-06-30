from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import ContractModel
from .briefing import DatasetBriefing
from .dataset import DatasetMetadata


class DatasetSession(ContractModel):
    session_id: str
    dataset_id: str
    metadata: DatasetMetadata
    semantic_summary: str = ""
    dataset_briefing: DatasetBriefing | None = None
    memory_summary: str = ""
    suggested_questions: list[dict[str, Any]] = Field(default_factory=list)
    turn_ids: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
