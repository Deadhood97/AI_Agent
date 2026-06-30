from __future__ import annotations

from uuid import uuid4

from contracts.memory import MemoryRecord
from core.artifacts import ArtifactStore
from core.tracing import utc_now_iso


def new_memory_id() -> str:
    return f"memory-{uuid4().hex}"


class MemoryStore:
    def __init__(self, artifact_store: ArtifactStore):
        self.artifact_store = artifact_store

    def add(
        self,
        session_id: str,
        memory_type: str,
        summary: str,
        turn_id: str | None = None,
        artifact_ids: list[str] | None = None,
    ) -> MemoryRecord:
        record = MemoryRecord.model_validate(
            {
                "memory_id": new_memory_id(),
                "session_id": session_id,
                "turn_id": turn_id,
                "memory_type": memory_type,
                "summary": summary,
                "artifact_ids": artifact_ids or [],
                "created_at": utc_now_iso(),
            }
        )
        self.artifact_store.write_json("memory", record.memory_id, record.model_dump())
        return record

    def get(self, memory_id: str) -> MemoryRecord:
        return MemoryRecord.model_validate(self.artifact_store.read_json("memory", memory_id))

    def list_for_session(self, session_id: str) -> list[MemoryRecord]:
        memory_dir = self.artifact_store.root / "memory"
        if not memory_dir.exists():
            return []
        records: list[MemoryRecord] = []
        for path in sorted(memory_dir.glob("*.json")):
            record = MemoryRecord.model_validate_json(path.read_text(encoding="utf-8"))
            if record.session_id == session_id:
                records.append(record)
        return records

    def recent_for_session(self, session_id: str, limit: int = 8) -> list[MemoryRecord]:
        return self.list_for_session(session_id)[-limit:]


def build_memory_context(records: list[MemoryRecord]) -> str:
    if not records:
        return "No prior memory records."
    lines = ["Memory records:"]
    for record in records:
        turn_suffix = f" from {record.turn_id}" if record.turn_id else ""
        artifact_suffix = ""
        if record.artifact_ids:
            artifact_suffix = f" Artifacts: {', '.join(record.artifact_ids)}."
        lines.append(f"- {record.memory_type}{turn_suffix}: {record.summary}{artifact_suffix}")
    return "\n".join(lines)
