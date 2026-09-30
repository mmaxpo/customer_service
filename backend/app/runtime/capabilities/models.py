from __future__ import annotations

import time
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CapabilityInvocationStatus(StrEnum):
    OK = "ok"
    ERROR = "error"


class CapabilityInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    user_id: Any = None
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at_ts: float = Field(default_factory=time.time)


class CapabilityResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: CapabilityInvocationStatus
    capability_id: str
    output: Any = None
    error_code: str | None = None
    error_message: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == CapabilityInvocationStatus.OK
