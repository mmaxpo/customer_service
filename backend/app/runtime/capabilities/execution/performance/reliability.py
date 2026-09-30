from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CapabilityReliabilityRecommendation(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class CapabilityProviderReliabilityReport(BaseModel):
    """
    Read-only reliability interpretation of durable performance evidence.

    A report is advisory evidence. It does not mutate provider health,
    availability, or provider-selection state.
    """

    model_config = ConfigDict(extra="forbid")

    capability_id: str
    provider_id: str | None = None
    provider_ref: str | None = None
    tenant_id: str | None = None

    window_start: datetime
    window_end: datetime

    attempts: int = Field(ge=0)
    successes: int = Field(ge=0)
    failures: int = Field(ge=0)

    timeouts: int = Field(ge=0)
    unavailable: int = Field(ge=0)
    circuit_open: int = Field(ge=0)
    provider_errors: int = Field(ge=0)
    other_failures: int = Field(ge=0)

    fallback_eligible_failures: int = Field(ge=0)
    fallback_recoveries: int = Field(ge=0)
    fallback_invocations: int = Field(ge=0)

    success_rate: float = Field(ge=0.0, le=1.0)
    failure_rate: float = Field(ge=0.0, le=1.0)
    timeout_rate: float = Field(ge=0.0, le=1.0)
    provider_error_rate: float = Field(ge=0.0, le=1.0)
    fallback_recovery_rate: float = Field(ge=0.0, le=1.0)

    average_duration_ms: float = Field(ge=0.0)

    minimum_attempts: int = Field(ge=1)
    evidence_sufficient: bool
    recommendation: CapabilityReliabilityRecommendation


class CapabilityReliabilityPolicy:
    """
    Configurable interpretation policy for provider evidence.

    Defaults:
      fewer than 10 attempts -> insufficient evidence
      success rate >= 98%    -> healthy
      success rate >= 90%    -> degraded
      otherwise              -> unhealthy
    """

    def __init__(
        self,
        *,
        minimum_attempts: int = 10,
        healthy_success_rate: float = 0.98,
        degraded_success_rate: float = 0.90,
    ) -> None:
        if minimum_attempts < 1:
            raise ValueError("minimum_attempts must be >= 1")

        if not 0.0 <= degraded_success_rate <= 1.0:
            raise ValueError(
                "degraded_success_rate must be between 0 and 1"
            )

        if not 0.0 <= healthy_success_rate <= 1.0:
            raise ValueError(
                "healthy_success_rate must be between 0 and 1"
            )

        if degraded_success_rate > healthy_success_rate:
            raise ValueError(
                "degraded_success_rate cannot exceed "
                "healthy_success_rate"
            )

        self.minimum_attempts = minimum_attempts
        self.healthy_success_rate = healthy_success_rate
        self.degraded_success_rate = degraded_success_rate

    def recommend(
        self,
        *,
        attempts: int,
        success_rate: float,
    ) -> CapabilityReliabilityRecommendation:
        if attempts < self.minimum_attempts:
            return (
                CapabilityReliabilityRecommendation
                .INSUFFICIENT_EVIDENCE
            )

        if success_rate >= self.healthy_success_rate:
            return CapabilityReliabilityRecommendation.HEALTHY

        if success_rate >= self.degraded_success_rate:
            return CapabilityReliabilityRecommendation.DEGRADED

        return CapabilityReliabilityRecommendation.UNHEALTHY


__all__ = [
    "CapabilityProviderReliabilityReport",
    "CapabilityReliabilityPolicy",
    "CapabilityReliabilityRecommendation",
]
