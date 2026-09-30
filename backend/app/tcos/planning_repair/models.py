from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RepairStrategyType(StrEnum):
    REPLAN = "replan"
    ESCALATE = "escalate"


class RepairPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: RepairStrategyType
    reason: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    actions: list[dict] = Field(default_factory=list)


class RepairResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repairable: bool
    plan: RepairPlan | None = None
    issues: list[dict] = Field(default_factory=list)
