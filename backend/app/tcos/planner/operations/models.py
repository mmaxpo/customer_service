from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OperationType(StrEnum):
    ACQUIRE_INFORMATION = "acquire_information"
    ANALYZE = "analyze"
    DECIDE = "decide"
    EXECUTE = "execute"
    COMMUNICATE = "communicate"


class PlanningOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    capability_id: str
    operation_type: OperationType
    purpose: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
