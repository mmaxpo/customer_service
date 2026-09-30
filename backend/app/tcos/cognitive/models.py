from __future__ import annotations

import time
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class CognitiveSessionStatus(StrEnum):
    CREATED = "created"
    COMPLETED = "completed"
    FAILED = "failed"


class CognitiveEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class CognitiveSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    goal: str
    status: CognitiveSessionStatus = CognitiveSessionStatus.CREATED
    planner_session: dict[str, Any] | None = None
    execution_session: dict[str, Any] | None = None
    events: list[CognitiveEvent] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)

    def record(self, event_type: str, **payload: Any) -> None:
        self.events.append(CognitiveEvent(type=event_type, payload=payload))
