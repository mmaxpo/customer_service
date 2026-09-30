from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class TaskVerificationOutcome(StrEnum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"
    NOT_VERIFIABLE = "not_verifiable"


class TaskVerificationMethod(StrEnum):
    REMOTE_STATE = "remote_state"
    EXECUTION_EVIDENCE = "execution_evidence"


class TaskVerificationEvidence(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    kind: str
    source: str
    observed_at_ts: float = Field(
        default_factory=time.time
    )
    data: dict[str, Any] = Field(
        default_factory=dict
    )


class TaskVerificationRequest(BaseModel):
    """
    Stable request for verifying one business task outcome.

    The request carries the original intent and technical execution output.
    A verifier must independently decide whether that evidence is sufficient
    or whether fresh provider state is required.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    verification_id: str = Field(
        default_factory=lambda: str(
            uuid.uuid4()
        )
    )

    capability_id: str = Field(
        min_length=1
    )
    provider_id: str | None = None
    provider_ref: str | None = None
    action: str | None = None

    user_id: str | None = None
    tenant_id: str | None = None

    correlation_id: str | None = None
    workflow_run_id: str | None = None
    task_id: str | None = None

    inputs: dict[str, Any] = Field(
        default_factory=dict
    )
    expected_outcome: dict[str, Any] = Field(
        default_factory=dict
    )
    execution_output: Any = None
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    requested_at_ts: float = Field(
        default_factory=time.time
    )


class TaskVerificationResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    verification_id: str
    capability_id: str
    provider_id: str | None = None
    provider_ref: str | None = None
    action: str | None = None

    outcome: TaskVerificationOutcome
    method: TaskVerificationMethod

    reason_code: str
    summary: str
    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )
    retryable: bool = False

    observed_outcome: dict[str, Any] = Field(
        default_factory=dict
    )
    evidence: list[
        TaskVerificationEvidence
    ] = Field(
        default_factory=list
    )

    completed_at_ts: float = Field(
        default_factory=time.time
    )


class TaskVerificationExecution(BaseModel):
    """
    Result returned by the orchestration service.

    created=False means the idempotency key already identified a durable
    attempt, so no remote verifier or lifecycle event was executed again.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    record_id: str
    attempt_number: int = Field(
        ge=1
    )
    created: bool
    result: TaskVerificationResult


@dataclass(frozen=True)
class TaskVerificationContext:
    request: TaskVerificationRequest
    services: Any = None


@runtime_checkable
class TaskVerifier(Protocol):
    async def verify(
        self,
        context: TaskVerificationContext,
    ) -> TaskVerificationResult:
        ...


__all__ = [
    "TaskVerificationContext",
    "TaskVerificationEvidence",
    "TaskVerificationExecution",
    "TaskVerificationMethod",
    "TaskVerificationOutcome",
    "TaskVerificationRequest",
    "TaskVerificationResult",
    "TaskVerifier",
]
