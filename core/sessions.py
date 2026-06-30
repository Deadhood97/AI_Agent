from __future__ import annotations

from uuid import uuid4

from contracts import ConversationTurn, DatasetMetadata, DatasetSession
from core.artifacts import ArtifactStore
from core.tracing import utc_now_iso


def new_session_id() -> str:
    return f"session-{uuid4().hex}"


def new_turn_id() -> str:
    return f"turn-{uuid4().hex}"


def create_dataset_session(
    dataset_id: str,
    metadata: DatasetMetadata | dict,
    semantic_summary: str = "",
    suggested_questions: list[dict] | None = None,
    store: ArtifactStore | None = None,
) -> DatasetSession:
    now = utc_now_iso()
    session = DatasetSession.model_validate(
        {
            "session_id": new_session_id(),
            "dataset_id": dataset_id,
            "metadata": DatasetMetadata.model_validate(metadata).model_dump(),
            "semantic_summary": semantic_summary,
            "memory_summary": "",
            "suggested_questions": suggested_questions or [],
            "turn_ids": [],
            "created_at": now,
            "updated_at": now,
        }
    )
    if store is not None:
        save_session(store, session)
    return session


def save_session(store: ArtifactStore, session: DatasetSession) -> None:
    store.write_json("sessions", session.session_id, session.model_dump())


def load_session(store: ArtifactStore, session_id: str) -> DatasetSession:
    return DatasetSession.model_validate(store.read_json("sessions", session_id))


def save_turn(store: ArtifactStore, turn: ConversationTurn) -> None:
    store.write_json("turns", turn.turn_id, turn.model_dump())


def load_turn(store: ArtifactStore, turn_id: str) -> ConversationTurn:
    return ConversationTurn.model_validate(store.read_json("turns", turn_id))


def attach_turn_to_session(
    session: DatasetSession,
    turn: ConversationTurn,
    store: ArtifactStore | None = None,
) -> DatasetSession:
    turn_ids = list(session.turn_ids)
    if turn.turn_id not in turn_ids:
        turn_ids.append(turn.turn_id)
    updated = session.model_copy(update={"turn_ids": turn_ids, "updated_at": utc_now_iso()})
    if store is not None:
        save_session(store, updated)
        save_turn(store, turn)
    return updated
