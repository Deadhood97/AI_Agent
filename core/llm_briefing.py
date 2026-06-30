from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from contracts import DatasetBriefing
from core.dataset_metadata import compact_metadata_for_context
from core.langsmith_tracing import end_langsmith_span, langsmith_span


LLM_BRIEFING_VERSION = "openai-briefing-v0"


class LLMBriefingUnavailable(RuntimeError):
    """Raised when the optional OpenAI dataset briefing cannot run."""


def ai_briefing_enabled() -> bool:
    load_dotenv(".env")
    return os.getenv("OPENAI_BRIEFING_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _api_key() -> str:
    load_dotenv(".env")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "your_key_here":
        raise LLMBriefingUnavailable("OPENAI_API_KEY is not configured.")
    return api_key


def build_openai_dataset_briefing(metadata: dict[str, Any], deterministic_briefing: DatasetBriefing) -> DatasetBriefing:
    api_key = _api_key()
    try:
        from openai import OpenAI
    except Exception as exc:
        raise LLMBriefingUnavailable(
            "The `openai` package is not installed. Install agent dependencies before enabling OpenAI briefing."
        ) from exc

    model = os.getenv("OPENAI_BRIEFING_MODEL") or os.getenv("OPENAI_ANSWER_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
    compact_metadata = compact_metadata_for_context(metadata)
    system_prompt = (
        "You are a careful dataset analyst. Return a DatasetBriefing JSON object only. "
        "Use only the provided metadata and deterministic fallback briefing. Do not invent row counts, "
        "column counts, column names, or numerical facts. Prefer useful, concrete starter questions "
        "that can be answered from the listed columns. Keep wording concise and product-facing."
    )
    user_prompt = {
        "metadata": compact_metadata,
        "fallback_briefing": deterministic_briefing.model_dump(),
        "dataset_briefing_schema": DatasetBriefing.model_json_schema(),
        "required_generator": "openai",
        "briefing_version": LLM_BRIEFING_VERSION,
    }

    with langsmith_span(
        "build_openai_dataset_briefing",
        run_type="llm",
        inputs={"metadata": compact_metadata, "model": model},
    ) as span:
        client = OpenAI(api_key=api_key)
        response = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": repr(user_prompt)},
            ],
            text_format=DatasetBriefing,
        )
        briefing = response.output_parsed
        if briefing is None:
            raise ValueError("OpenAI response did not include a parsed DatasetBriefing.")

        briefing = briefing.model_copy(
            update={
                "row_count": int(metadata.get("row_count") or deterministic_briefing.row_count),
                "column_count": int(metadata.get("column_count") or deterministic_briefing.column_count),
                "generator": "openai",
                "model": model,
                "suggested_questions": briefing.suggested_questions or deterministic_briefing.suggested_questions,
                "assumptions": briefing.assumptions or deterministic_briefing.assumptions,
                "limitations": briefing.limitations or deterministic_briefing.limitations,
            }
        )
        end_langsmith_span(
            span,
            {
                "generator": briefing.generator,
                "model": model,
                "question_count": len(briefing.suggested_questions),
                "key_metrics": briefing.key_metrics,
                "key_dimensions": briefing.key_dimensions,
            },
        )
        return briefing
