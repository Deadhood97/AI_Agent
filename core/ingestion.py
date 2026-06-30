from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts import DatasetBriefing, DatasetMetadata
from core.artifacts import ArtifactStore, dataset_id_for
from core.csv_io import read_csv_bytes
from core.dataset_briefing import build_dataset_briefing
from core.dataset_metadata import build_dataset_metadata
from core.kaggle_import import fetch_kaggle_dataset
from core.langsmith_tracing import (
    compact_metadata_for_langsmith,
    end_langsmith_span,
    langsmith_span,
    summarize_suggestions_for_langsmith,
    summarize_trace_events_for_langsmith,
)
from core.llm_briefing import ai_briefing_enabled, build_openai_dataset_briefing
from core.question_suggestions import SuggestedQuestion, suggest_questions
from core.sessions import create_dataset_session
from core.tracing import append_trace_event


@dataclass(frozen=True)
class DatasetIngestionResult:
    dataset_id: str
    session_id: str
    metadata: DatasetMetadata
    suggested_questions: list[SuggestedQuestion]
    dataset_briefing: DatasetBriefing
    parser: str
    trace: list[dict[str, Any]]


class DatasetIngestionService:
    def __init__(self, artifact_store: ArtifactStore, kaggle_fetcher=fetch_kaggle_dataset):
        self.artifact_store = artifact_store
        self._fetch_kaggle_dataset = kaggle_fetcher

    def ingest_csv_bytes(
        self,
        raw_bytes: bytes,
        filename: str,
        dataset_description: str = "",
        semantic_summary: str = "",
    ) -> DatasetIngestionResult:
        with langsmith_span(
            "DatasetTools.ingest_csv_bytes",
            run_type="chain",
            inputs={"filename": filename, "description_provided": bool(dataset_description)},
        ) as span:
            trace: list[dict[str, Any]] = []
            append_trace_event(trace, "read_csv", "started", {"filename": filename})
            df, parser = read_csv_bytes(raw_bytes)
            append_trace_event(
                trace,
                "read_csv",
                "succeeded",
                {"parser": parser, "rows": int(len(df)), "columns": int(len(df.columns))},
            )

            metadata_payload = build_dataset_metadata(df, filename, raw_bytes, dataset_description)
            metadata = DatasetMetadata.model_validate(metadata_payload)
            dataset_id = dataset_id_for(metadata.model_dump())
            append_trace_event(
                trace,
                "build_dataset_metadata",
                "succeeded",
                {
                    "dataset_id": dataset_id,
                    "row_count": metadata.row_count,
                    "column_count": metadata.column_count,
                },
            )
            suggested_questions = suggest_questions(metadata.model_dump())
            dataset_briefing = build_dataset_briefing(metadata.model_dump(), suggested_questions)
            append_trace_event(
                trace,
                "build_dataset_briefing",
                "succeeded",
                {"generator": dataset_briefing.generator, "question_count": len(dataset_briefing.suggested_questions)},
            )
            if ai_briefing_enabled():
                try:
                    dataset_briefing = build_openai_dataset_briefing(metadata.model_dump(), dataset_briefing)
                    suggested_questions = dataset_briefing.suggested_questions[:3] or suggested_questions
                    append_trace_event(
                        trace,
                        "build_openai_dataset_briefing",
                        "succeeded",
                        {
                            "generator": dataset_briefing.generator,
                            "model": dataset_briefing.model,
                            "question_count": len(dataset_briefing.suggested_questions),
                        },
                    )
                except Exception as exc:
                    append_trace_event(
                        trace,
                        "build_openai_dataset_briefing",
                        "failed",
                        {"fallback": "deterministic"},
                        error_message=str(exc),
                    )
            append_trace_event(
                trace,
                "suggest_questions",
                "succeeded",
                {
                    "questions": [suggestion.question for suggestion in suggested_questions],
                    "briefing_generator": dataset_briefing.generator,
                },
            )
            session = create_dataset_session(
                dataset_id,
                metadata,
                semantic_summary=semantic_summary or dataset_briefing.summary,
                dataset_briefing=dataset_briefing.model_dump(),
                suggested_questions=[suggestion.model_dump() for suggestion in suggested_questions],
                store=self.artifact_store,
            )

            self.artifact_store.write_bytes("datasets", dataset_id, raw_bytes, suffix=".csv")
            self.artifact_store.write_json("metadata", dataset_id, metadata.model_dump())
            self.artifact_store.write_json("briefings", dataset_id, dataset_briefing.model_dump())
            self.artifact_store.write_json("traces", f"{session.session_id}-ingest", trace)

            end_langsmith_span(
                span,
                {
                    "dataset_id": dataset_id,
                    "session_id": session.session_id,
                    "parser": parser,
                    "suggested_questions": summarize_suggestions_for_langsmith(suggested_questions),
                    "briefing": {
                        "summary": dataset_briefing.summary,
                        "generator": dataset_briefing.generator,
                        "model": dataset_briefing.model,
                        "key_metrics": dataset_briefing.key_metrics,
                        "key_dimensions": dataset_briefing.key_dimensions,
                        "quality_warning_count": len(dataset_briefing.quality_warnings),
                    },
                    "trace_events": summarize_trace_events_for_langsmith(trace),
                    "metadata": compact_metadata_for_langsmith(metadata.model_dump()),
                },
            )
            return DatasetIngestionResult(
                dataset_id=dataset_id,
                session_id=session.session_id,
                metadata=metadata,
                suggested_questions=suggested_questions,
                dataset_briefing=dataset_briefing,
                parser=parser,
                trace=trace,
            )

    def ingest_kaggle_dataset(
        self,
        dataset_ref: str,
        requested_file: str = "",
        dataset_description: str = "",
        semantic_summary: str = "",
    ) -> DatasetIngestionResult:
        with langsmith_span(
            "DatasetTools.ingest_kaggle_dataset",
            run_type="chain",
            inputs={
                "dataset_ref": dataset_ref,
                "requested_file": requested_file,
                "description_provided": bool(dataset_description),
            },
        ) as span:
            kaggle_import = self._fetch_kaggle_dataset(
                dataset_ref,
                requested_file=requested_file,
                download_root=self.artifact_store.root / "kaggle_downloads",
            )
            description_parts = [
                str(kaggle_import.get("description") or "").strip(),
                dataset_description.strip(),
            ]
            combined_description = "\n\n".join(part for part in description_parts if part)
            result = self.ingest_csv_bytes(
                raw_bytes=kaggle_import["raw_bytes"],
                filename=str(kaggle_import["filename"]),
                dataset_description=combined_description,
                semantic_summary=semantic_summary,
            )
            end_langsmith_span(
                span,
                {
                    "dataset_ref": kaggle_import.get("dataset_ref"),
                    "selected_file": kaggle_import.get("selected_file"),
                    "filename": kaggle_import.get("filename"),
                    "download_path": str(kaggle_import.get("download_path", "")),
                    "available_file_count": len(kaggle_import.get("files", [])),
                    "dataset_id": result.dataset_id,
                    "session_id": result.session_id,
                    "suggested_questions": summarize_suggestions_for_langsmith(result.suggested_questions),
                },
            )
            return result
