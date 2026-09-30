from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BusinessLearningObservation(BaseModel):
    """
    Immutable normalized evidence about one evaluated
    business objective.

    The observation is descriptive only. It does not
    directly mutate planning, workflow construction,
    routing, policy, or runtime behavior.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    source_event_id: UUID
    source_evaluation_record_id: UUID
    source_outcome_record_id: UUID

    user_id: UUID
    tenant_id: str | None = None

    objective_namespace: str
    objective_ref: str
    objective_type: str

    source_objective_version: int = Field(
        ge=1
    )
    outcome_version: int = Field(
        ge=1
    )
    evaluation_version: int = Field(
        ge=1
    )

    result: str
    reason_code: str
    summary: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )
    retryable: bool
    is_final: bool

    decision: str
    outcome_status: str
    operation_count: int = Field(
        ge=0
    )

    achieved_operation_count: int = Field(
        ge=0
    )
    failed_operation_count: int = Field(
        ge=0
    )
    pending_operation_count: int = Field(
        ge=0
    )
    unknown_operation_count: int = Field(
        ge=0
    )
    not_executed_operation_count: int = Field(
        ge=0
    )

    workflow_run_id: str | None = None
    conversation_id: str | None = None
    chat_session_id: str | None = None

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
    "BusinessLearningObservation",
]
