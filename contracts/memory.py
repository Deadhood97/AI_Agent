from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ContractModel


class MemoryRecord(ContractModel):
    memory_id: str
    session_id: str
    turn_id: str | None = None
    memory_type: Literal["dataset", "conversation", "analytical"]
    summary: str
    artifact_ids: list[str] = Field(default_factory=list)
    created_at: str

