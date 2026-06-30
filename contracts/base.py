from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict

ModelT = TypeVar("ModelT", bound=BaseModel)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def validate_contract(model_type: type[ModelT], payload: Any) -> ModelT:
    if isinstance(payload, model_type):
        return payload
    return model_type.model_validate(payload)

