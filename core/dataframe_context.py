from __future__ import annotations

import json
from typing import Any

import pandas as pd

from core.dataset_metadata import compact_metadata_for_context, json_safe


def dataframe_preview_records(df: pd.DataFrame, rows: int = 5) -> list[dict[str, Any]]:
    preview = df.head(rows)
    return [
        {str(key): json_safe(value) for key, value in row.items()}
        for row in preview.to_dict(orient="records")
    ]


def dataframe_markdown_preview(df: pd.DataFrame, rows: int = 5) -> str:
    return df.head(rows).to_markdown(index=False)


def build_dataframe_context(
    metadata: dict[str, Any],
    df: pd.DataFrame,
    rows: int = 5,
    max_description_chars: int = 1600,
) -> str:
    compact_metadata = compact_metadata_for_context(
        metadata,
        max_description_chars=max_description_chars,
    )
    return (
        "Dataset context JSON:\n"
        f"{json.dumps(compact_metadata, indent=2)}\n\n"
        f"First {rows} dataframe rows:\n{dataframe_markdown_preview(df, rows=rows)}"
    )


def build_tool_context_payload(metadata: dict[str, Any], df: pd.DataFrame, rows: int = 5) -> dict[str, Any]:
    return {
        "metadata": compact_metadata_for_context(metadata),
        "preview_rows": dataframe_preview_records(df, rows=rows),
    }
