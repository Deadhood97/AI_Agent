from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_numeric_dtype


def json_safe(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def infer_column_role(series: pd.Series) -> str:
    if is_datetime64_any_dtype(series):
        return "temporal"
    if is_bool_dtype(series):
        return "boolean"
    if is_numeric_dtype(series):
        return "numeric"
    unique_ratio = series.nunique(dropna=True) / max(len(series), 1)
    if unique_ratio <= 0.2:
        return "categorical"
    return "text"


def analyze_columns(df: pd.DataFrame) -> list[dict[str, Any]]:
    columns: list[dict[str, Any]] = []
    for column in df.columns:
        series = df[column]
        non_null = series.dropna()
        profile: dict[str, Any] = {
            "name": str(column),
            "pandas_dtype": str(series.dtype),
            "inferred_role": infer_column_role(series),
            "row_count": int(len(series)),
            "null_count": int(series.isna().sum()),
            "null_percentage": round(float(series.isna().mean() * 100), 2),
            "unique_count": int(series.nunique(dropna=True)),
            "sample_values": [json_safe(value) for value in non_null.head(5).tolist()],
        }
        if is_numeric_dtype(series) and not is_bool_dtype(series):
            profile["statistics"] = {
                "min": json_safe(series.min()),
                "max": json_safe(series.max()),
                "mean": json_safe(series.mean()),
                "median": json_safe(series.median()),
            }
        else:
            value_counts = non_null.astype(str).value_counts().head(12)
            profile["top_values"] = [
                {"value": json_safe(index), "count": int(count)}
                for index, count in value_counts.items()
            ]
        columns.append(profile)
    return columns


def data_integrity_summary(df: pd.DataFrame) -> dict[str, Any]:
    total_cells = int(df.shape[0] * df.shape[1])
    missing_cells = int(df.isna().sum().sum())
    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "missing_cells": missing_cells,
        "missing_percentage": round((missing_cells / total_cells) * 100, 2) if total_cells else 0,
        "duplicate_rows": int(df.duplicated().sum()),
    }


def build_dataset_metadata(
    df: pd.DataFrame,
    filename: str,
    raw_bytes: bytes,
    dataset_description: str = "",
) -> dict[str, Any]:
    columns = analyze_columns(df)
    return {
        "source_file": filename,
        "file_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_description": dataset_description,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": columns,
        "data_integrity": data_integrity_summary(df),
    }


def compact_metadata_for_context(metadata: dict[str, Any], max_description_chars: int = 1600) -> dict[str, Any]:
    description = metadata.get("dataset_description", "")
    if len(description) > max_description_chars:
        description = description[: max_description_chars - 3].rstrip() + "..."
    return {
        "source_file": metadata.get("source_file"),
        "row_count": metadata.get("row_count"),
        "column_count": metadata.get("column_count"),
        "dataset_description": description,
        "columns": [
            {
                "name": column.get("name"),
                "pandas_dtype": column.get("pandas_dtype"),
                "inferred_role": column.get("inferred_role"),
                "null_count": column.get("null_count"),
                "unique_count": column.get("unique_count"),
                "statistics": column.get("statistics"),
                "sample_values": (column.get("sample_values") or [])[:3],
                "top_values": (column.get("top_values") or [])[:5],
            }
            for column in metadata.get("columns", [])
        ],
    }


def build_dataframe_context(metadata: dict[str, Any], df: pd.DataFrame, rows: int = 5) -> str:
    from core.dataframe_context import build_dataframe_context as build_context

    return build_context(metadata, df, rows=rows)
