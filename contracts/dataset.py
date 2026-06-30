from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import ContractModel


class DatasetProfileColumn(ContractModel):
    name: str
    pandas_dtype: str
    inferred_role: str
    row_count: int
    null_count: int
    null_percentage: float
    unique_count: int
    sample_values: list[Any] = Field(default_factory=list)
    statistics: dict[str, Any] | None = None
    top_values: list[dict[str, Any]] = Field(default_factory=list)


class DatasetMetadata(ContractModel):
    source_file: str
    file_sha256: str
    created_at: str
    dataset_description: str = ""
    row_count: int
    column_count: int
    columns: list[DatasetProfileColumn]
    data_integrity: dict[str, Any] = Field(default_factory=dict)

