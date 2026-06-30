from __future__ import annotations

from typing import Any

from contracts import ConversationTurn, ResolvedIntent, SuggestedQuestion
from core.analysis_turns import AnalysisTurnService
from core.artifacts import ArtifactStore
from core.dataset_sessions import DatasetSessionService
from core.ingestion import DatasetIngestionResult, DatasetIngestionService
from core.kaggle_import import fetch_kaggle_dataset


class DatasetTools:
    """Compatibility facade for dataset analyst workflows.

    The public API stays intentionally small while implementation work lives in
    focused services. UI, tests, and learning labs can continue calling this
    facade as the app grows.
    """

    def __init__(self, artifact_store: ArtifactStore | None = None):
        self.artifact_store = artifact_store or ArtifactStore()
        self._sessions = DatasetSessionService(self.artifact_store)
        self._ingestion = DatasetIngestionService(self.artifact_store, kaggle_fetcher=fetch_kaggle_dataset)
        self._turns = AnalysisTurnService(self.artifact_store, self._sessions)

    def ingest_csv_bytes(
        self,
        raw_bytes: bytes,
        filename: str,
        dataset_description: str = "",
        semantic_summary: str = "",
    ) -> DatasetIngestionResult:
        return self._ingestion.ingest_csv_bytes(
            raw_bytes=raw_bytes,
            filename=filename,
            dataset_description=dataset_description,
            semantic_summary=semantic_summary,
        )

    def ingest_kaggle_dataset(
        self,
        dataset_ref: str,
        requested_file: str = "",
        dataset_description: str = "",
        semantic_summary: str = "",
    ) -> DatasetIngestionResult:
        return self._ingestion.ingest_kaggle_dataset(
            dataset_ref=dataset_ref,
            requested_file=requested_file,
            dataset_description=dataset_description,
            semantic_summary=semantic_summary,
        )

    def load_dataframe_for_session(self, session_id: str):
        return self._sessions.load_dataframe_for_session(session_id)

    def preview_for_session(self, session_id: str, rows: int = 5) -> dict[str, Any]:
        return self._sessions.preview_for_session(session_id, rows=rows)

    def suggest_questions_for_session(self, session_id: str, limit: int = 3) -> list[SuggestedQuestion]:
        return self._sessions.suggest_questions_for_session(session_id, limit=limit)

    def run_analysis_turn(
        self,
        session_id: str,
        user_message: str,
        code: str,
        output_key: str | None = None,
        resolved_intent: ResolvedIntent | dict | None = None,
        analysis_plan: dict[str, Any] | None = None,
    ) -> ConversationTurn:
        return self._turns.run_analysis_turn(
            session_id=session_id,
            user_message=user_message,
            code=code,
            output_key=output_key,
            resolved_intent=resolved_intent,
            analysis_plan=analysis_plan,
        )

    def run_planned_turn(self, session_id: str, user_message: str, allow_llm: bool = False) -> ConversationTurn:
        return self._turns.run_planned_turn(
            session_id=session_id,
            user_message=user_message,
            allow_llm=allow_llm,
        )
