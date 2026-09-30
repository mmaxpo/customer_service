from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CapabilityLearningObservation(BaseModel):
    """
    Immutable reusable evidence derived from one task-verification attempt.

    This contract records business-outcome evidence only. It does not directly
    mutate provider preference, traffic allocation, health, or runtime policy.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    source_event_id: UUID
    source_verification_record_id: UUID

    verification_id: str
    attempt_number: int = Field(ge=1)

    user_id: UUID
    tenant_id: str | None = None

    capability_id: str
    provider_id: str | None = None
    provider_ref: str | None = None
    action: str | None = None

    outcome: str
    method: str
    reason_code: str
    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    retryable: bool
    is_final: bool

    correlation_id: str | None = None
    workflow_run_id: str | None = None
    task_id: str | None = None

    summary: str

    observed_outcome: dict[str, Any] = Field(
        default_factory=dict
    )
    evidence_summary: dict[str, Any] = Field(
        default_factory=dict
    )
    context: dict[str, Any] = Field(
        default_factory=dict
    )

    observed_at: datetime


__all__ = [
    "CapabilityLearningObservation",
]
