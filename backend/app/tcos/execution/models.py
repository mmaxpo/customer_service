from __future__ import annotations

import time
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ExecutionBackend(StrEnum):
    WORKFLOW_RUNTIME = "workflow_runtime"


class ExecutionStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class ExecutionSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    backend: ExecutionBackend
    status: ExecutionStatus = ExecutionStatus.CREATED

    execution_graph: dict

    runtime_workflow: dict | None = None
    runtime_result: dict | None = None

    events: list[ExecutionEvent] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)

    def record(self, event_type: str, **payload: Any) -> None:
        self.events.append(
            ExecutionEvent(
                type=event_type,
                payload=payload,
            )
        )
