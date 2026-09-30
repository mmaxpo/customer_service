from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.tcos.planner.runtime.plan_candidate import PlanCandidate


class MemoryCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: PlanCandidate
    similarity: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = "memory"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlanningMemoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    intent_name: str
    candidate: PlanCandidate

    success_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)

    average_latency_ms: float | None = Field(default=None, ge=0)
    average_cost: float | None = Field(default=None, ge=0)

    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    tenant_id: str | None = None
    user_id: str | None = None

    created_at_ts: float = Field(default_factory=time.time)
    updated_at_ts: float = Field(default_factory=time.time)
    last_used_at_ts: float | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_count(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        total = self.total_count
        if total == 0:
            return 0.0
        return self.success_count / total
