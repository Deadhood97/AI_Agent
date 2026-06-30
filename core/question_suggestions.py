from __future__ import annotations

from typing import Any

from contracts.briefing import SuggestedQuestion


def _columns_by_role(metadata: dict[str, Any], role: str) -> list[dict[str, Any]]:
    return [column for column in metadata.get("columns", []) if column.get("inferred_role") == role]


def _column_name(column: dict[str, Any]) -> str:
    return str(column.get("name") or "").strip()


def _best_numeric_column(metadata: dict[str, Any]) -> str | None:
    numeric_columns = _columns_by_role(metadata, "numeric")
    if not numeric_columns:
        return None

    def score(column: dict[str, Any]) -> tuple[int, int]:
        name = _column_name(column).lower()
        business_words = ["revenue", "sales", "amount", "price", "profit", "cost", "total", "value"]
        business_score = 1 if any(word in name for word in business_words) else 0
        unique_count = int(column.get("unique_count") or 0)
        return business_score, unique_count

    return _column_name(sorted(numeric_columns, key=score, reverse=True)[0])


def _best_group_column(metadata: dict[str, Any]) -> str | None:
    candidates = _columns_by_role(metadata, "categorical") + _columns_by_role(metadata, "text")
    candidates = [column for column in candidates if _column_name(column)]
    if not candidates:
        return None

    row_count = max(int(metadata.get("row_count") or 0), 1)

    def score(column: dict[str, Any]) -> tuple[int, int]:
        unique_count = int(column.get("unique_count") or 0)
        is_reasonable_group = 1 if 1 < unique_count <= min(25, row_count) else 0
        return is_reasonable_group, -unique_count

    return _column_name(sorted(candidates, key=score, reverse=True)[0])


def suggest_questions(metadata: dict[str, Any], limit: int = 3) -> list[SuggestedQuestion]:
    suggestions: list[SuggestedQuestion] = []
    numeric_column = _best_numeric_column(metadata)
    group_column = _best_group_column(metadata)

    if numeric_column:
        suggestions.append(
            SuggestedQuestion(
                question=f"What is the total {numeric_column}?",
                rationale=f"'{numeric_column}' is a numeric column, so a total is a useful first metric.",
                question_type="analysis",
                columns=[numeric_column],
                priority=1,
                expected_visualization="kpi",
            )
        )

    if group_column:
        suggestions.append(
            SuggestedQuestion(
                question=f"Count by {group_column}",
                rationale=f"'{group_column}' can segment the dataset into groups.",
                question_type="visualization",
                columns=[group_column],
                priority=1,
                expected_visualization="bar",
            )
        )

    if numeric_column:
        suggestions.append(
            SuggestedQuestion(
                question=f"What is the average {numeric_column}?",
                rationale=f"'{numeric_column}' is numeric, so the average gives a quick baseline.",
                question_type="analysis",
                columns=[numeric_column],
                priority=2,
                expected_visualization="kpi",
            )
        )

    suggestions.append(
        SuggestedQuestion(
            question="How many rows are there?",
            rationale="Row count is a simple sanity check after upload.",
            question_type="summary",
            columns=[],
            priority=3,
            expected_visualization="kpi",
        )
    )

    unique: list[SuggestedQuestion] = []
    seen_questions: set[str] = set()
    for suggestion in suggestions:
        if suggestion.question in seen_questions:
            continue
        seen_questions.add(suggestion.question)
        unique.append(suggestion)
        if len(unique) == limit:
            break
    return unique
