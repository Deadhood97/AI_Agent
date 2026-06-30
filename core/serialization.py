from __future__ import annotations

from typing import Any

import pandas as pd

from core.dataset_metadata import json_safe


def serialize_analysis_output(value: Any, max_rows: int = 200) -> dict[str, Any]:
    if isinstance(value, pd.DataFrame):
        frame = value.head(max_rows)
        return {
            "kind": "table",
            "type": "DataFrame",
            "columns": [str(column) for column in frame.columns],
            "rows": [
                {str(key): json_safe(cell) for key, cell in row.items()}
                for row in frame.to_dict(orient="records")
            ],
            "row_count": int(len(value)),
            "truncated": len(value) > max_rows,
        }
    if isinstance(value, pd.Series):
        return serialize_analysis_output(value.reset_index(), max_rows=max_rows) | {"type": "Series"}
    if isinstance(value, dict):
        return {"kind": "mapping", "type": "dict", "value": {str(key): json_safe(cell) for key, cell in value.items()}}
    if isinstance(value, (list, tuple)):
        return serialize_analysis_output(pd.DataFrame(value), max_rows=max_rows)
    return {"kind": "scalar", "type": type(value).__name__, "value": json_safe(value)}


def serialize_analysis_outputs(outputs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {key: serialize_analysis_output(value) for key, value in outputs.items()}

