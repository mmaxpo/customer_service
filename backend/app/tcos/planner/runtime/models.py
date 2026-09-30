from __future__ import annotations

import time
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.tcos.compiler.result import CompilationResult
from app.tcos.planner.business_ir.models import BusinessPlan


class PlanningStatus(StrEnum):
    CREATED = "created"
    PLANNING = "planning"
    CLARIFICATION_REQUIRED = "clarification_required"
    COMPILED = "compiled"
    FAILED = "failed"


class PlannerEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class PlannerSession(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str | None = None
    tenant_id: str | None = None
    goal: str
    context: dict[str, Any] = Field(default_factory=dict)
    status: PlanningStatus = PlanningStatus.CREATED
    business_plan: BusinessPlan | None = None
    compilation: CompilationResult | None = None

    selected_candidate: dict[str, Any] | None = None
    clarification: dict[str, Any] | None = None
    verification_result: dict[str, Any] | None = None
    repair_result: dict[str, Any] | None = None
    learning_episode: dict[str, Any] | None = None
    events: list[PlannerEvent] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)

    def record(self, event_type: str, **payload: Any) -> None:
        self.events.append(PlannerEvent(type=event_type, payload=payload))
