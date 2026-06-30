from __future__ import annotations

from uuid import uuid4

from contracts import ChartPayload, ResolvedIntent
from contracts.analysis import SerializedAnalysisOutput


def recommend_chart_payload(
    output_key: str | None,
    output: SerializedAnalysisOutput | None,
    intent: ResolvedIntent,
) -> ChartPayload | None:
    if output_key is None or output is None:
        return None

    if output.kind == "scalar":
        return ChartPayload(
            chart_id=f"chart-{uuid4().hex}",
            chart_type="kpi",
            source_output_key=output_key,
            title=output_key.replace("_", " ").title(),
            rationale="A single computed value is best shown as a KPI.",
        )

    if output.kind == "table" and output.columns and output.rows:
        if len(output.columns) >= 2:
            x_column = intent.grouping[0] if intent.grouping and intent.grouping[0] in output.columns else output.columns[0]
            y_candidates = [column for column in output.columns if column != x_column]
            y_column = "count" if "count" in y_candidates else y_candidates[0] if y_candidates else None
            if y_column:
                return ChartPayload(
                    chart_id=f"chart-{uuid4().hex}",
                    chart_type="bar",
                    source_output_key=output_key,
                    title=output_key.replace("_", " ").title(),
                    x=x_column,
                    y=y_column,
                    top_n=min(int(output.row_count or len(output.rows)), 12),
                    rationale="Grouped table output can be compared clearly with a bar chart.",
                )

    return None
