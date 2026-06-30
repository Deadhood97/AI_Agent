from __future__ import annotations

from typing import Any

from core.artifacts import ArtifactStore
from core.csv_io import read_csv_bytes
from core.dataframe_context import build_tool_context_payload
from core.langsmith_tracing import (
    compact_metadata_for_langsmith,
    end_langsmith_span,
    langsmith_span,
    summarize_suggestions_for_langsmith,
)
from core.question_suggestions import SuggestedQuestion, suggest_questions
from core.sessions import load_session


class DatasetSessionService:
    def __init__(self, artifact_store: ArtifactStore):
        self.artifact_store = artifact_store

    def load_dataframe_for_session(self, session_id: str):
        session = load_session(self.artifact_store, session_id)
        raw_bytes = self.artifact_store.read_bytes("datasets", session.dataset_id, suffix=".csv")
        df, _parser = read_csv_bytes(raw_bytes)
        return df, session

    def preview_for_session(self, session_id: str, rows: int = 5) -> dict[str, Any]:
        with langsmith_span(
            "DatasetTools.preview_for_session",
            run_type="tool",
            inputs={"session_id": session_id, "rows": rows},
        ) as span:
            df, session = self.load_dataframe_for_session(session_id)
            payload = build_tool_context_payload(session.metadata.model_dump(), df, rows=rows)
            end_langsmith_span(
                span,
                {
                    "dataset_id": session.dataset_id,
                    "metadata": compact_metadata_for_langsmith(session.metadata.model_dump()),
                    "preview_rows": payload["preview_rows"],
                },
            )
            return payload

    def suggest_questions_for_session(self, session_id: str, limit: int = 3) -> list[SuggestedQuestion]:
        with langsmith_span(
            "DatasetTools.suggest_questions_for_session",
            run_type="tool",
            inputs={"session_id": session_id, "limit": limit},
        ) as span:
            session = load_session(self.artifact_store, session_id)
            if session.suggested_questions:
                suggestions = [
                    SuggestedQuestion(
                        question=str(suggestion.get("question", "")),
                        rationale=str(suggestion.get("rationale", "")),
                        question_type=str(suggestion.get("question_type", "analysis")),
                        columns=[str(column) for column in suggestion.get("columns", [])],
                    )
                    for suggestion in session.suggested_questions[:limit]
                ]
            else:
                suggestions = suggest_questions(session.metadata.model_dump(), limit=limit)
            end_langsmith_span(
                span,
                {
                    "dataset_id": session.dataset_id,
                    "suggested_questions": summarize_suggestions_for_langsmith(suggestions),
                },
            )
            return suggestions
