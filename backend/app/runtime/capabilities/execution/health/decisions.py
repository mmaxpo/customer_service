from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.runtime.capabilities.execution.performance.reliability import (
    CapabilityProviderReliabilityReport,
    CapabilityReliabilityRecommendation,
)


class ProviderHealthState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RECOVERING = "recovering"


class ProviderHealthDecisionAction(StrEnum):
    HOLD = "hold"
    PROPOSE_TRANSITION = "propose_transition"


class ProviderHealthDecisionReason(StrEnum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    COOLDOWN_ACTIVE = "cooldown_active"
    STABLE = "stable"

    DEGRADATION_PENDING = "degradation_pending"
    DEGRADATION_CONFIRMED = "degradation_confirmed"

    UNHEALTHY_PENDING = "unhealthy_pending"
    UNHEALTHY_CONFIRMED = "unhealthy_confirmed"

    RECOVERY_PENDING = "recovery_pending"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_CONFIRMED = "recovery_confirmed"

    RECOVERY_REGRESSED = "recovery_regressed"


class ProviderHealthDecisionScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    capability_id: str
    provider_id: str
    provider_ref: str | None = None
    tenant_id: str | None = None


class ProposedProviderHealthDecision(BaseModel):
    """
    Advisory provider-health decision.

    This contract intentionally does not mutate ProviderHealthRegistry,
    provider bindings, or runtime selection state.
    """

    model_config = ConfigDict(extra="forbid")

    scope: ProviderHealthDecisionScope

    current_state: ProviderHealthState
    proposed_state: ProviderHealthState

    action: ProviderHealthDecisionAction
    reason: ProviderHealthDecisionReason

    evidence_recommendation: (
        CapabilityReliabilityRecommendation
    )
    evidence_sufficient: bool

    attempts: int = Field(ge=0)
    successes: int = Field(ge=0)
    failures: int = Field(ge=0)
    success_rate: float = Field(ge=0.0, le=1.0)

    qualifying_windows: int = Field(ge=0)
    required_windows: int = Field(ge=1)

    window_start: datetime
    window_end: datetime

    cooldown_until: datetime | None = None
    evaluated_at: datetime

    explanation: str

    @property
    def transition_proposed(self) -> bool:
        return (
            self.action
            == ProviderHealthDecisionAction.PROPOSE_TRANSITION
        )


class ProviderHealthDecisionPolicy:
    """
    Convert reliability evidence into a guarded proposed transition.

    Consecutive-window counts and cooldown timestamps are provided by the
    caller. A later durable state repository will calculate and persist those
    values. This policy remains deterministic and side-effect free.
    """

    def __init__(
        self,
        *,
        degrade_after_windows: int = 2,
        unhealthy_after_windows: int = 3,
        recover_after_windows: int = 2,
    ) -> None:
        for name, value in (
            (
                "degrade_after_windows",
                degrade_after_windows,
            ),
            (
                "unhealthy_after_windows",
                unhealthy_after_windows,
            ),
            (
                "recover_after_windows",
                recover_after_windows,
            ),
        ):
            if value < 1:
                raise ValueError(
                    f"{name} must be >= 1"
                )

        if unhealthy_after_windows < degrade_after_windows:
            raise ValueError(
                "unhealthy_after_windows cannot be lower than "
                "degrade_after_windows"
            )

        self.degrade_after_windows = (
            degrade_after_windows
        )
        self.unhealthy_after_windows = (
            unhealthy_after_windows
        )
        self.recover_after_windows = (
            recover_after_windows
        )

    def decide(
        self,
        *,
        user_id: str,
        report: CapabilityProviderReliabilityReport,
        current_state: ProviderHealthState = (
            ProviderHealthState.HEALTHY
        ),
        qualifying_windows: int = 1,
        cooldown_until: datetime | None = None,
        evaluated_at: datetime | None = None,
    ) -> ProposedProviderHealthDecision:
        now = evaluated_at or datetime.now(timezone.utc)

        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        normalized_cooldown = cooldown_until
        if (
            normalized_cooldown is not None
            and normalized_cooldown.tzinfo is None
        ):
            normalized_cooldown = (
                normalized_cooldown.replace(
                    tzinfo=timezone.utc
                )
            )

        provider_id = str(
            report.provider_id or ""
        ).strip()

        if not provider_id:
            raise ValueError(
                "reliability report provider_id is required"
            )

        scope = ProviderHealthDecisionScope(
            user_id=str(user_id),
            capability_id=report.capability_id,
            provider_id=provider_id,
            provider_ref=report.provider_ref,
            tenant_id=report.tenant_id,
        )

        if not report.evidence_sufficient:
            return self._hold(
                scope=scope,
                report=report,
                current_state=current_state,
                reason=(
                    ProviderHealthDecisionReason
                    .INSUFFICIENT_EVIDENCE
                ),
                qualifying_windows=qualifying_windows,
                required_windows=report.minimum_attempts,
                cooldown_until=normalized_cooldown,
                evaluated_at=now,
                explanation=(
                    "The reliability window does not contain "
                    "enough attempts to propose a health change."
                ),
            )

        if (
            current_state
            in {
                ProviderHealthState.UNHEALTHY,
                ProviderHealthState.RECOVERING,
            }
            and normalized_cooldown is not None
            and now < normalized_cooldown
        ):
            return self._hold(
                scope=scope,
                report=report,
                current_state=current_state,
                reason=(
                    ProviderHealthDecisionReason
                    .COOLDOWN_ACTIVE
                ),
                qualifying_windows=qualifying_windows,
                required_windows=(
                    self.recover_after_windows
                ),
                cooldown_until=normalized_cooldown,
                evaluated_at=now,
                explanation=(
                    "The provider remains inside its health "
                    "transition cooldown period."
                ),
            )

        recommendation = report.recommendation

        if current_state == ProviderHealthState.HEALTHY:
            return self._from_healthy(
                scope=scope,
                report=report,
                recommendation=recommendation,
                qualifying_windows=qualifying_windows,
                cooldown_until=normalized_cooldown,
                evaluated_at=now,
            )

        if current_state == ProviderHealthState.DEGRADED:
            return self._from_degraded(
                scope=scope,
                report=report,
                recommendation=recommendation,
                qualifying_windows=qualifying_windows,
                cooldown_until=normalized_cooldown,
                evaluated_at=now,
            )

        if current_state == ProviderHealthState.UNHEALTHY:
            return self._from_unhealthy(
                scope=scope,
                report=report,
                recommendation=recommendation,
                qualifying_windows=qualifying_windows,
                cooldown_until=normalized_cooldown,
                evaluated_at=now,
            )

        return self._from_recovering(
            scope=scope,
            report=report,
            recommendation=recommendation,
            qualifying_windows=qualifying_windows,
            cooldown_until=normalized_cooldown,
            evaluated_at=now,
        )

    def _from_healthy(
        self,
        *,
        scope: ProviderHealthDecisionScope,
        report: CapabilityProviderReliabilityReport,
        recommendation: CapabilityReliabilityRecommendation,
        qualifying_windows: int,
        cooldown_until: datetime | None,
        evaluated_at: datetime,
    ) -> ProposedProviderHealthDecision:
        if (
            recommendation
            == CapabilityReliabilityRecommendation.HEALTHY
        ):
            return self._stable(
                scope=scope,
                report=report,
                state=ProviderHealthState.HEALTHY,
                qualifying_windows=qualifying_windows,
                cooldown_until=cooldown_until,
                evaluated_at=evaluated_at,
            )

        if (
            recommendation
            == CapabilityReliabilityRecommendation.UNHEALTHY
        ):
            if (
                qualifying_windows
                >= self.unhealthy_after_windows
            ):
                return self._transition(
                    scope=scope,
                    report=report,
                    current_state=ProviderHealthState.HEALTHY,
                    proposed_state=(
                        ProviderHealthState.UNHEALTHY
                    ),
                    reason=(
                        ProviderHealthDecisionReason
                        .UNHEALTHY_CONFIRMED
                    ),
                    qualifying_windows=qualifying_windows,
                    required_windows=(
                        self.unhealthy_after_windows
                    ),
                    cooldown_until=cooldown_until,
                    evaluated_at=evaluated_at,
                    explanation=(
                        "Unhealthy reliability evidence was "
                        "confirmed across the required windows."
                    ),
                )

            return self._hold(
                scope=scope,
                report=report,
                current_state=ProviderHealthState.HEALTHY,
                reason=(
                    ProviderHealthDecisionReason
                    .UNHEALTHY_PENDING
                ),
                qualifying_windows=qualifying_windows,
                required_windows=(
                    self.unhealthy_after_windows
                ),
                cooldown_until=cooldown_until,
                evaluated_at=evaluated_at,
                explanation=(
                    "Unhealthy evidence exists but has not "
                    "persisted for enough consecutive windows."
                ),
            )

        if qualifying_windows >= self.degrade_after_windows:
            return self._transition(
                scope=scope,
                report=report,
                current_state=ProviderHealthState.HEALTHY,
                proposed_state=ProviderHealthState.DEGRADED,
                reason=(
                    ProviderHealthDecisionReason
                    .DEGRADATION_CONFIRMED
                ),
                qualifying_windows=qualifying_windows,
                required_windows=self.degrade_after_windows,
                cooldown_until=cooldown_until,
                evaluated_at=evaluated_at,
                explanation=(
                    "Degraded reliability evidence was "
                    "confirmed across the required windows."
                ),
            )

        return self._hold(
            scope=scope,
            report=report,
            current_state=ProviderHealthState.HEALTHY,
            reason=(
                ProviderHealthDecisionReason
                .DEGRADATION_PENDING
            ),
            qualifying_windows=qualifying_windows,
            required_windows=self.degrade_after_windows,
            cooldown_until=cooldown_until,
            evaluated_at=evaluated_at,
            explanation=(
                "Degraded evidence exists but has not "
                "persisted for enough consecutive windows."
            ),
        )

    def _from_degraded(
        self,
        *,
        scope: ProviderHealthDecisionScope,
        report: CapabilityProviderReliabilityReport,
        recommendation: CapabilityReliabilityRecommendation,
        qualifying_windows: int,
        cooldown_until: datetime | None,
        evaluated_at: datetime,
    ) -> ProposedProviderHealthDecision:
        if (
            recommendation
            == CapabilityReliabilityRecommendation.UNHEALTHY
        ):
            if (
                qualifying_windows
                >= self.unhealthy_after_windows
            ):
                return self._transition(
                    scope=scope,
                    report=report,
                    current_state=(
                        ProviderHealthState.DEGRADED
                    ),
                    proposed_state=(
                        ProviderHealthState.UNHEALTHY
                    ),
                    reason=(
                        ProviderHealthDecisionReason
                        .UNHEALTHY_CONFIRMED
                    ),
                    qualifying_windows=qualifying_windows,
                    required_windows=(
                        self.unhealthy_after_windows
                    ),
                    cooldown_until=cooldown_until,
                    evaluated_at=evaluated_at,
                    explanation=(
                        "The degraded provider has continued "
                        "to produce unhealthy evidence."
                    ),
                )

            return self._hold(
                scope=scope,
                report=report,
                current_state=ProviderHealthState.DEGRADED,
                reason=(
                    ProviderHealthDecisionReason
                    .UNHEALTHY_PENDING
                ),
                qualifying_windows=qualifying_windows,
                required_windows=(
                    self.unhealthy_after_windows
                ),
                cooldown_until=cooldown_until,
                evaluated_at=evaluated_at,
                explanation=(
                    "Unhealthy evidence has not persisted "
                    "for enough windows."
                ),
            )

        if (
            recommendation
            == CapabilityReliabilityRecommendation.HEALTHY
        ):
            if (
                qualifying_windows
                >= self.recover_after_windows
            ):
                return self._transition(
                    scope=scope,
                    report=report,
                    current_state=(
                        ProviderHealthState.DEGRADED
                    ),
                    proposed_state=(
                        ProviderHealthState.HEALTHY
                    ),
                    reason=(
                        ProviderHealthDecisionReason
                        .RECOVERY_CONFIRMED
                    ),
                    qualifying_windows=qualifying_windows,
                    required_windows=(
                        self.recover_after_windows
                    ),
                    cooldown_until=cooldown_until,
                    evaluated_at=evaluated_at,
                    explanation=(
                        "Healthy evidence persisted for the "
                        "required recovery windows."
                    ),
                )

            return self._hold(
                scope=scope,
                report=report,
                current_state=ProviderHealthState.DEGRADED,
                reason=(
                    ProviderHealthDecisionReason
                    .RECOVERY_PENDING
                ),
                qualifying_windows=qualifying_windows,
                required_windows=(
                    self.recover_after_windows
                ),
                cooldown_until=cooldown_until,
                evaluated_at=evaluated_at,
                explanation=(
                    "Recovery evidence exists but requires "
                    "additional healthy windows."
                ),
            )

        return self._stable(
            scope=scope,
            report=report,
            state=ProviderHealthState.DEGRADED,
            qualifying_windows=qualifying_windows,
            cooldown_until=cooldown_until,
            evaluated_at=evaluated_at,
        )

    def _from_unhealthy(
        self,
        *,
        scope: ProviderHealthDecisionScope,
        report: CapabilityProviderReliabilityReport,
        recommendation: CapabilityReliabilityRecommendation,
        qualifying_windows: int,
        cooldown_until: datetime | None,
        evaluated_at: datetime,
    ) -> ProposedProviderHealthDecision:
        if (
            recommendation
            == CapabilityReliabilityRecommendation.HEALTHY
        ):
            return self._transition(
                scope=scope,
                report=report,
                current_state=ProviderHealthState.UNHEALTHY,
                proposed_state=(
                    ProviderHealthState.RECOVERING
                ),
                reason=(
                    ProviderHealthDecisionReason
                    .RECOVERY_STARTED
                ),
                qualifying_windows=qualifying_windows,
                required_windows=1,
                cooldown_until=cooldown_until,
                evaluated_at=evaluated_at,
                explanation=(
                    "A healthy evidence window permits the "
                    "provider to enter guarded recovery."
                ),
            )

        return self._stable(
            scope=scope,
            report=report,
            state=ProviderHealthState.UNHEALTHY,
            qualifying_windows=qualifying_windows,
            cooldown_until=cooldown_until,
            evaluated_at=evaluated_at,
        )

    def _from_recovering(
        self,
        *,
        scope: ProviderHealthDecisionScope,
        report: CapabilityProviderReliabilityReport,
        recommendation: CapabilityReliabilityRecommendation,
        qualifying_windows: int,
        cooldown_until: datetime | None,
        evaluated_at: datetime,
    ) -> ProposedProviderHealthDecision:
        if (
            recommendation
            == CapabilityReliabilityRecommendation.HEALTHY
        ):
            if (
                qualifying_windows
                >= self.recover_after_windows
            ):
                return self._transition(
                    scope=scope,
                    report=report,
                    current_state=(
                        ProviderHealthState.RECOVERING
                    ),
                    proposed_state=(
                        ProviderHealthState.HEALTHY
                    ),
                    reason=(
                        ProviderHealthDecisionReason
                        .RECOVERY_CONFIRMED
                    ),
                    qualifying_windows=qualifying_windows,
                    required_windows=(
                        self.recover_after_windows
                    ),
                    cooldown_until=cooldown_until,
                    evaluated_at=evaluated_at,
                    explanation=(
                        "Recovery remained healthy across "
                        "the required consecutive windows."
                    ),
                )

            return self._hold(
                scope=scope,
                report=report,
                current_state=(
                    ProviderHealthState.RECOVERING
                ),
                reason=(
                    ProviderHealthDecisionReason
                    .RECOVERY_PENDING
                ),
                qualifying_windows=qualifying_windows,
                required_windows=(
                    self.recover_after_windows
                ),
                cooldown_until=cooldown_until,
                evaluated_at=evaluated_at,
                explanation=(
                    "The provider is recovering but needs "
                    "additional healthy evidence."
                ),
            )

        if (
            recommendation
            == CapabilityReliabilityRecommendation.UNHEALTHY
        ):
            return self._transition(
                scope=scope,
                report=report,
                current_state=(
                    ProviderHealthState.RECOVERING
                ),
                proposed_state=(
                    ProviderHealthState.UNHEALTHY
                ),
                reason=(
                    ProviderHealthDecisionReason
                    .RECOVERY_REGRESSED
                ),
                qualifying_windows=qualifying_windows,
                required_windows=1,
                cooldown_until=cooldown_until,
                evaluated_at=evaluated_at,
                explanation=(
                    "Unhealthy evidence returned during "
                    "provider recovery."
                ),
            )

        return self._hold(
            scope=scope,
            report=report,
            current_state=ProviderHealthState.RECOVERING,
            reason=(
                ProviderHealthDecisionReason
                .RECOVERY_PENDING
            ),
            qualifying_windows=qualifying_windows,
            required_windows=(
                self.recover_after_windows
            ),
            cooldown_until=cooldown_until,
            evaluated_at=evaluated_at,
            explanation=(
                "Degraded evidence is not sufficient to "
                "complete recovery."
            ),
        )

    @staticmethod
    def _stable(
        *,
        scope: ProviderHealthDecisionScope,
        report: CapabilityProviderReliabilityReport,
        state: ProviderHealthState,
        qualifying_windows: int,
        cooldown_until: datetime | None,
        evaluated_at: datetime,
    ) -> ProposedProviderHealthDecision:
        return ProviderHealthDecisionPolicy._hold(
            scope=scope,
            report=report,
            current_state=state,
            reason=ProviderHealthDecisionReason.STABLE,
            qualifying_windows=qualifying_windows,
            required_windows=1,
            cooldown_until=cooldown_until,
            evaluated_at=evaluated_at,
            explanation=(
                "The evidence supports keeping the current "
                "provider health state."
            ),
        )

    @staticmethod
    def _hold(
        *,
        scope: ProviderHealthDecisionScope,
        report: CapabilityProviderReliabilityReport,
        current_state: ProviderHealthState,
        reason: ProviderHealthDecisionReason,
        qualifying_windows: int,
        required_windows: int,
        cooldown_until: datetime | None,
        evaluated_at: datetime,
        explanation: str,
    ) -> ProposedProviderHealthDecision:
        return ProposedProviderHealthDecision(
            scope=scope,
            current_state=current_state,
            proposed_state=current_state,
            action=ProviderHealthDecisionAction.HOLD,
            reason=reason,
            evidence_recommendation=report.recommendation,
            evidence_sufficient=report.evidence_sufficient,
            attempts=report.attempts,
            successes=report.successes,
            failures=report.failures,
            success_rate=report.success_rate,
            qualifying_windows=qualifying_windows,
            required_windows=required_windows,
            window_start=report.window_start,
            window_end=report.window_end,
            cooldown_until=cooldown_until,
            evaluated_at=evaluated_at,
            explanation=explanation,
        )

    @staticmethod
    def _transition(
        *,
        scope: ProviderHealthDecisionScope,
        report: CapabilityProviderReliabilityReport,
        current_state: ProviderHealthState,
        proposed_state: ProviderHealthState,
        reason: ProviderHealthDecisionReason,
        qualifying_windows: int,
        required_windows: int,
        cooldown_until: datetime | None,
        evaluated_at: datetime,
        explanation: str,
    ) -> ProposedProviderHealthDecision:
        return ProposedProviderHealthDecision(
            scope=scope,
            current_state=current_state,
            proposed_state=proposed_state,
            action=(
                ProviderHealthDecisionAction
                .PROPOSE_TRANSITION
            ),
            reason=reason,
            evidence_recommendation=report.recommendation,
            evidence_sufficient=report.evidence_sufficient,
            attempts=report.attempts,
            successes=report.successes,
            failures=report.failures,
            success_rate=report.success_rate,
            qualifying_windows=qualifying_windows,
            required_windows=required_windows,
            window_start=report.window_start,
            window_end=report.window_end,
            cooldown_until=cooldown_until,
            evaluated_at=evaluated_at,
            explanation=explanation,
        )


__all__ = [
    "ProposedProviderHealthDecision",
    "ProviderHealthDecisionAction",
    "ProviderHealthDecisionPolicy",
    "ProviderHealthDecisionReason",
    "ProviderHealthDecisionScope",
    "ProviderHealthState",
]
