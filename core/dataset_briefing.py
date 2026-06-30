from __future__ import annotations

from typing import Any

from contracts.briefing import ColumnInsight, DatasetBriefing, DatasetQualityWarning, SuggestedQuestion


BUSINESS_METRIC_WORDS = ("revenue", "sales", "amount", "price", "profit", "cost", "total", "value", "score")


def _column_name(column: dict[str, Any]) -> str:
    return str(column.get("name") or "").strip()


def _columns_by_role(metadata: dict[str, Any], role: str) -> list[dict[str, Any]]:
    return [column for column in metadata.get("columns", []) if column.get("inferred_role") == role]


def _best_numeric_columns(metadata: dict[str, Any], limit: int = 3) -> list[str]:
    numeric_columns = _columns_by_role(metadata, "numeric")

    def score(column: dict[str, Any]) -> tuple[int, int]:
        name = _column_name(column).lower()
        business_score = 1 if any(word in name for word in BUSINESS_METRIC_WORDS) else 0
        unique_count = int(column.get("unique_count") or 0)
        return business_score, unique_count

    return [_column_name(column) for column in sorted(numeric_columns, key=score, reverse=True)[:limit] if _column_name(column)]


def _best_dimension_columns(metadata: dict[str, Any], limit: int = 4) -> list[str]:
    row_count = max(int(metadata.get("row_count") or 0), 1)
    candidates = _columns_by_role(metadata, "categorical") + _columns_by_role(metadata, "text")

    def score(column: dict[str, Any]) -> tuple[int, int]:
        unique_count = int(column.get("unique_count") or 0)
        is_groupable = 1 if 1 < unique_count <= min(30, row_count) else 0
        return is_groupable, -unique_count

    return [_column_name(column) for column in sorted(candidates, key=score, reverse=True)[:limit] if _column_name(column)]


def _time_fields(metadata: dict[str, Any]) -> list[str]:
    return [_column_name(column) for column in _columns_by_role(metadata, "temporal") if _column_name(column)]


def _column_insights(metadata: dict[str, Any], limit: int = 8) -> list[ColumnInsight]:
    insights: list[ColumnInsight] = []
    for column in metadata.get("columns", [])[:limit]:
        name = _column_name(column)
        if not name:
            continue
        role = str(column.get("inferred_role") or "unknown")
        missing = float(column.get("null_percentage") or 0)
        unique_count = int(column.get("unique_count") or 0)
        warnings = []
        if missing >= 25:
            warnings.append(f"{missing:.1f}% missing values")
        if unique_count <= 1:
            warnings.append("low variation")
        summary = f"{name} appears to be {role} with {unique_count} unique values."
        if role == "numeric" and column.get("statistics"):
            stats = column["statistics"]
            summary = f"{name} is numeric, ranging from {stats.get('min')} to {stats.get('max')}."
        insights.append(
            ColumnInsight(
                name=name,
                role=role,
                summary=summary,
                missing_percentage=missing,
                unique_count=unique_count,
                warnings=warnings,
            )
        )
    return insights


def _quality_warnings(metadata: dict[str, Any]) -> list[DatasetQualityWarning]:
    warnings: list[DatasetQualityWarning] = []
    integrity = metadata.get("data_integrity") or {}
    missing_percentage = float(integrity.get("missing_percentage") or 0)
    duplicate_rows = int(integrity.get("duplicate_rows") or 0)
    if missing_percentage > 0:
        severity = "warning" if missing_percentage >= 10 else "info"
        warnings.append(
            DatasetQualityWarning(
                severity=severity,
                message=f"{missing_percentage:.2f}% of cells are missing.",
            )
        )
    if duplicate_rows:
        warnings.append(
            DatasetQualityWarning(
                severity="warning",
                message=f"{duplicate_rows} duplicate rows were detected.",
            )
        )
    for column in metadata.get("columns", []):
        missing = float(column.get("null_percentage") or 0)
        if missing >= 25:
            warnings.append(
                DatasetQualityWarning(
                    severity="warning",
                    message=f"{_column_name(column)} has {missing:.1f}% missing values.",
                    columns=[_column_name(column)],
                )
            )
    return warnings


def _briefing_questions(metadata: dict[str, Any], metrics: list[str], dimensions: list[str], time_fields: list[str]) -> list[SuggestedQuestion]:
    questions: list[SuggestedQuestion] = [
        SuggestedQuestion(
            question="What is in this dataset?",
            rationale="Start by understanding the dataset shape and important fields.",
            question_type="summary",
            priority=1,
        )
    ]
    if metrics:
        questions.append(
            SuggestedQuestion(
                question=f"What is the total {metrics[0]}?",
                rationale=f"{metrics[0]} is a likely metric column.",
                question_type="analysis",
                columns=[metrics[0]],
                priority=1,
                expected_visualization="kpi",
            )
        )
        questions.append(
            SuggestedQuestion(
                question=f"What is the average {metrics[0]}?",
                rationale=f"Averages provide a useful baseline for {metrics[0]}.",
                question_type="analysis",
                columns=[metrics[0]],
                priority=2,
                expected_visualization="kpi",
            )
        )
    if dimensions:
        questions.append(
            SuggestedQuestion(
                question=f"Count by {dimensions[0]}",
                rationale=f"{dimensions[0]} is a useful grouping dimension.",
                question_type="visualization",
                columns=[dimensions[0]],
                priority=1,
                expected_visualization="bar",
            )
        )
    if metrics and dimensions:
        questions.append(
            SuggestedQuestion(
                question=f"Which {dimensions[0]} has the highest {metrics[0]}?",
                rationale="Ranking a metric by a dimension is a common first insight.",
                question_type="visualization",
                columns=[dimensions[0], metrics[0]],
                priority=2,
                expected_visualization="bar",
            )
        )
    if time_fields and metrics:
        questions.append(
            SuggestedQuestion(
                question=f"How does {metrics[0]} change over {time_fields[0]}?",
                rationale="A time field and metric can support trend analysis.",
                question_type="visualization",
                columns=[time_fields[0], metrics[0]],
                priority=2,
                expected_visualization="line",
            )
        )
    return questions[:6]


def build_dataset_briefing(metadata: dict[str, Any], suggested_questions: list[SuggestedQuestion] | None = None) -> DatasetBriefing:
    metrics = _best_numeric_columns(metadata)
    dimensions = _best_dimension_columns(metadata)
    time_fields = _time_fields(metadata)
    source = str(metadata.get("source_file") or "dataset")
    row_count = int(metadata.get("row_count") or 0)
    column_count = int(metadata.get("column_count") or 0)
    likely_subject = source.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()

    metric_phrase = f" Likely metrics include {', '.join(metrics[:3])}." if metrics else ""
    dimension_phrase = f" Useful dimensions include {', '.join(dimensions[:3])}." if dimensions else ""
    summary = f"{source} contains {row_count:,} rows and {column_count:,} columns.{metric_phrase}{dimension_phrase}".strip()
    briefing_questions = _briefing_questions(metadata, metrics, dimensions, time_fields)
    if suggested_questions:
        for question in suggested_questions:
            if question.question not in {existing.question for existing in briefing_questions}:
                briefing_questions.append(question)

    return DatasetBriefing(
        summary=summary,
        row_count=row_count,
        column_count=column_count,
        likely_subject=likely_subject,
        key_metrics=metrics,
        key_dimensions=dimensions,
        time_fields=time_fields,
        column_insights=_column_insights(metadata),
        quality_warnings=_quality_warnings(metadata),
        suggested_questions=briefing_questions[:6],
        assumptions=["Column roles are inferred from pandas dtypes, cardinality, and column names."],
        limitations=["This deterministic briefing does not infer domain meaning beyond metadata patterns."],
    )
