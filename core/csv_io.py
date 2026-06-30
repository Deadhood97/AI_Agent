from __future__ import annotations

from io import BytesIO
from typing import BinaryIO

import pandas as pd


class CsvReadError(ValueError):
    """Raised when a CSV cannot be parsed by any supported strategy."""


def read_csv_bytes(raw_bytes: bytes) -> tuple[pd.DataFrame, str]:
    """Read uploaded CSV bytes with tolerant parser fallbacks."""
    attempts = [
        ("default pandas C parser", {"engine": "c"}),
        ("python parser comma", {"engine": "python", "sep": ","}),
        ("python parser semicolon", {"engine": "python", "sep": ";"}),
        ("python parser flexible", {"engine": "python", "sep": None}),
    ]
    errors: list[str] = []

    for label, kwargs in attempts:
        try:
            frame = pd.read_csv(BytesIO(raw_bytes), **kwargs)
            if frame.empty and len(frame.columns) == 0:
                raise ValueError("CSV produced no columns.")
            return frame, label
        except Exception as exc:
            errors.append(f"{label}: {type(exc).__name__}: {exc}")

    raise CsvReadError("Could not parse CSV. Attempts: " + " | ".join(errors))


def read_csv_file(file: BinaryIO) -> tuple[pd.DataFrame, str, bytes]:
    """Read a binary file-like object and return dataframe, parser label, and raw bytes."""
    raw_bytes = file.read()
    frame, parser = read_csv_bytes(raw_bytes)
    return frame, parser, raw_bytes

