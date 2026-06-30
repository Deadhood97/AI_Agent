from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from contracts import ResolvedIntent


class SimplePlanError(ValueError):
    """Raised when the deterministic planner cannot safely plan a question."""


@dataclass(frozen=True)
class SimpleAnalysisPlan:
    code: str
    resolved_intent: ResolvedIntent
    rationale: str


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _metadata_columns(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    return list(metadata.get("columns", []))


def _find_column(metadata: dict[str, Any], question: str, role: str | None = None) -> str | None:
    normalized_question = _normalize(question)
    candidates = _metadata_columns(metadata)
    if role is not None:
        role_candidates = [column for column in candidates if column.get("inferred_role") == role]
        candidates = role_candidates or candidates

    scored: list[tuple[int, str]] = []
    for column in candidates:
        name = str(column.get("name", ""))
        normalized_name = _normalize(name)
        if not normalized_name:
            continue
        if normalized_name in normalized_question:
            scored.append((len(normalized_name), name))
    if scored:
        return sorted(scored, reverse=True)[0][1]
    role_matches = [str(column.get("name")) for column in candidates if role is None or column.get("inferred_role") == role]
    return role_matches[0] if len(role_matches) == 1 else None


def plan_simple_question(question: str, metadata: dict[str, Any]) -> SimpleAnalysisPlan:
    normalized_question = _normalize(question)

    if any(phrase in normalized_question for phrase in ["how many rows", "row count", "number of rows"]):
        return SimpleAnalysisPlan(
            code="analysis_outputs = {'row_count': int(len(df))}",
            resolved_intent=ResolvedIntent(question_type="summary", requires_code=True, metrics=["row_count"]),
            rationale="Counted dataframe rows.",
        )

    if any(word in normalized_question.split() for word in ["total", "sum"]):
        column = _find_column(metadata, question, role="numeric")
        if column:
            return SimpleAnalysisPlan(
                code=f"analysis_outputs = {{'total_{column}': float(df[{column!r}].sum())}}",
                resolved_intent=ResolvedIntent(
                    question_type="analysis",
                    requires_code=True,
                    metrics=[f"sum:{column}"],
                ),
                rationale=f"Summed numeric column {column}.",
            )

    if any(word in normalized_question.split() for word in ["average", "mean"]):
        column = _find_column(metadata, question, role="numeric")
        if column:
            return SimpleAnalysisPlan(
                code=f"analysis_outputs = {{'average_{column}': float(df[{column!r}].mean())}}",
                resolved_intent=ResolvedIntent(
                    question_type="analysis",
                    requires_code=True,
                    metrics=[f"mean:{column}"],
                ),
                rationale=f"Averaged numeric column {column}.",
            )

    if " by " in f" {normalized_question} " or "group by" in normalized_question:
        column = _find_column(metadata, question, role="categorical")
        if column:
            output_name = f"count_by_{column}"
            code = (
                f"_counts = df[{column!r}].astype(str).value_counts().reset_index()\n"
                f"_counts.columns = [{column!r}, 'count']\n"
                f"analysis_outputs = {{{output_name!r}: _counts}}"
            )
            return SimpleAnalysisPlan(
                code=code,
                resolved_intent=ResolvedIntent(
                    question_type="analysis",
                    requires_code=True,
                    grouping=[column],
                    metrics=["count"],
                ),
                rationale=f"Counted rows grouped by {column}.",
            )

    raise SimplePlanError("The deterministic planner only supports row counts, sums, means, and simple group counts.")
