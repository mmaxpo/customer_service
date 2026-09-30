from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.health.decisions import (
    ProviderHealthDecisionPolicy,
    ProviderHealthState,
)
from app.runtime.capabilities.execution.health.persistence import (
    CapabilityProviderHealthPersistenceService,
)
from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
    normalize_user_id,
)
from app.runtime.capabilities.execution.performance.reliability import (
    CapabilityReliabilityPolicy,
    CapabilityReliabilityRecommendation,
)
from app.runtime.capabilities.execution.performance.reliability_service import (
    CapabilityReliabilityService,
)


class CapabilityHealthEvaluationRequest(BaseModel):
    """
    Deterministic input for one scoped health-evaluation window.

    window_end must be supplied by the scheduler or enqueueing caller. Worker
    retries therefore evaluate the same evidence window and produce the same
    idempotency key.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    tenant_id: str | None = None

    capability_id: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
    provider_ref: str | None = None

    window_hours: int = Field(default=24, ge=1, le=8760)
    window_end: datetime

    minimum_attempts: int = Field(default=10, ge=1)
    healthy_success_rate: float = Field(
        default=0.98,
        ge=0.0,
        le=1.0,
    )
    degraded_success_rate: float = Field(
        default=0.90,
        ge=0.0,
        le=1.0,
    )

    degrade_after_windows: int = Field(default=2, ge=1)
    unhealthy_after_windows: int = Field(default=3, ge=1)
    recover_after_windows: int = Field(default=2, ge=1)

    cooldown_seconds: int = Field(
        default=300,
        ge=0,
        le=604800,
    )

    def normalized_window_end(self) -> datetime:
        value = self.window_end

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)


class CapabilityHealthEvaluationService:
    """
    Orchestrate one deterministic scoped provider-health evaluation.

    This service persists advisory health state and decision history. It does
    not mutate ProviderHealthRegistry or provider-selection policy.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.health_repo = (
            CapabilityProviderHealthRepository(db)
        )
        self.persistence = (
            CapabilityProviderHealthPersistenceService(db)
        )

    async def evaluate(
        self,
        *,
        request: CapabilityHealthEvaluationRequest,
    ) -> dict[str, Any]:
        user_id = normalize_user_id(request.user_id)
        window_end = request.normalized_window_end()
        window_start = window_end - timedelta(
            hours=request.window_hours
        )

        existing_decision = (
            await self.health_repo.get_decision_for_window(
                user_id=user_id,
                tenant_id=request.tenant_id,
                capability_id=request.capability_id,
                provider_id=request.provider_id,
                provider_ref=request.provider_ref,
                window_start=window_start,
                window_end=window_end,
            )
        )

        if existing_decision is not None:
            return await self._existing_result(
                request=request,
                user_id=user_id,
                record=existing_decision,
            )

        latest_decision = (
            await self.health_repo.get_latest_decision(
                user_id=user_id,
                tenant_id=request.tenant_id,
                capability_id=request.capability_id,
                provider_id=request.provider_id,
                provider_ref=request.provider_ref,
            )
        )

        if (
            latest_decision is not None
            and window_end <= latest_decision.window_end
        ):
            return {
                "status": "stale",
                "user_id": str(user_id),
                "tenant_id": request.tenant_id,
                "capability_id": request.capability_id,
                "provider_id": request.provider_id,
                "provider_ref": request.provider_ref,
                "window_hours": request.window_hours,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
                "latest_window_end": (
                    latest_decision.window_end.isoformat()
                ),
                "persisted": False,
            }

        reliability_policy = CapabilityReliabilityPolicy(
            minimum_attempts=request.minimum_attempts,
            healthy_success_rate=(
                request.healthy_success_rate
            ),
            degraded_success_rate=(
                request.degraded_success_rate
            ),
        )

        reports = await CapabilityReliabilityService(
            self.db,
            policy=reliability_policy,
        ).summarize(
            user_id=user_id,
            tenant_id=request.tenant_id,
            capability_id=request.capability_id,
            provider_id=request.provider_id,
            provider_ref=request.provider_ref,
            window_hours=request.window_hours,
            now=window_end,
        )

        if not reports:
            return {
                "status": "no_evidence",
                "user_id": str(user_id),
                "tenant_id": request.tenant_id,
                "capability_id": request.capability_id,
                "provider_id": request.provider_id,
                "provider_ref": request.provider_ref,
                "window_hours": request.window_hours,
                "window_end": window_end.isoformat(),
                "persisted": False,
            }

        if len(reports) != 1:
            raise ValueError(
                "Health evaluation expected exactly one "
                "scoped reliability report"
            )

        report = reports[0]

        state = await self.health_repo.get_state(
            user_id=user_id,
            tenant_id=request.tenant_id,
            capability_id=request.capability_id,
            provider_id=request.provider_id,
            provider_ref=request.provider_ref,
        )

        current_state = (
            ProviderHealthState(state.current_state)
            if state is not None
            else ProviderHealthState.HEALTHY
        )

        qualifying_windows = (
            self._next_qualifying_windows(
                previous_decision=latest_decision,
                recommendation=report.recommendation,
                evidence_sufficient=(
                    report.evidence_sufficient
                ),
                window_start=report.window_start,
            )
        )

        cooldown_until = (
            state.cooldown_until
            if state is not None
            else None
        )

        decision_policy = ProviderHealthDecisionPolicy(
            degrade_after_windows=(
                request.degrade_after_windows
            ),
            unhealthy_after_windows=(
                request.unhealthy_after_windows
            ),
            recover_after_windows=(
                request.recover_after_windows
            ),
        )

        decision = decision_policy.decide(
            user_id=str(user_id),
            report=report,
            current_state=current_state,
            qualifying_windows=qualifying_windows,
            cooldown_until=cooldown_until,
            evaluated_at=window_end,
        )

        decision = self._apply_transition_cooldown(
            decision=decision,
            cooldown_seconds=request.cooldown_seconds,
        )

        persisted = await self.persistence.persist(
            decision=decision
        )

        return {
            "status": "evaluated",
            "user_id": str(user_id),
            "tenant_id": request.tenant_id,
            "capability_id": request.capability_id,
            "provider_id": request.provider_id,
            "provider_ref": request.provider_ref,
            "window_hours": request.window_hours,
            "window_start": (
                report.window_start.isoformat()
            ),
            "window_end": report.window_end.isoformat(),
            "recommendation": (
                report.recommendation.value
            ),
            "attempts": report.attempts,
            "success_rate": report.success_rate,
            "qualifying_windows": qualifying_windows,
            "decision": decision.model_dump(
                mode="json"
            ),
            "persistence": persisted,
            "persisted": True,
        }

    @staticmethod
    def _next_qualifying_windows(
        *,
        previous_decision,
        recommendation: (
            CapabilityReliabilityRecommendation
        ),
        evidence_sufficient: bool,
        window_start: datetime,
    ) -> int:
        # Insufficient evidence explicitly breaks a streak.
        if not evidence_sufficient:
            return 0

        if previous_decision is None:
            return 1

        adjacent = (
            previous_decision.window_end
            == window_start
        )
        same_recommendation = (
            previous_decision.evidence_sufficient
            and previous_decision
            .evidence_recommendation
            == recommendation.value
        )

        if adjacent and same_recommendation:
            return (
                int(
                    previous_decision
                    .qualifying_windows
                    or 0
                )
                + 1
            )

        return 1

    async def _existing_result(
        self,
        *,
        request: CapabilityHealthEvaluationRequest,
        user_id,
        record,
    ) -> dict[str, Any]:
        state = await self.health_repo.get_state(
            user_id=user_id,
            tenant_id=request.tenant_id,
            capability_id=request.capability_id,
            provider_id=request.provider_id,
            provider_ref=request.provider_ref,
        )

        if state is None:
            raise RuntimeError(
                "Persisted provider-health decision "
                "has no scoped state record"
            )

        return {
            "status": "evaluated",
            "user_id": str(user_id),
            "tenant_id": request.tenant_id,
            "capability_id": request.capability_id,
            "provider_id": request.provider_id,
            "provider_ref": request.provider_ref,
            "window_hours": request.window_hours,
            "window_start": (
                record.window_start.isoformat()
            ),
            "window_end": record.window_end.isoformat(),
            "recommendation": (
                record.evidence_recommendation
            ),
            "attempts": (
                record.evidence_json.get("attempts", 0)
            ),
            "success_rate": (
                record.evidence_json.get(
                    "success_rate",
                    0.0,
                )
            ),
            "qualifying_windows": (
                record.qualifying_windows
            ),
            "decision": record.evidence_json,
            "persistence": {
                "inserted": False,
                "state_id": str(state.id),
                "decision_id": str(record.id),
                "scope_key": state.scope_key,
                "current_state": state.current_state,
                "state_version": state.version,
                "decision_key": record.decision_key,
                "evaluation_key": (
                    record.evaluation_key
                ),
                "resulting_state": (
                    record.resulting_state
                ),
            },
            "persisted": True,
        }

    @staticmethod
    def _apply_transition_cooldown(
        *,
        decision,
        cooldown_seconds: int,
    ):
        if (
            not decision.transition_proposed
            or cooldown_seconds <= 0
        ):
            return decision

        from datetime import timedelta

        return decision.model_copy(
            update={
                "cooldown_until": (
                    decision.evaluated_at
                    + timedelta(seconds=cooldown_seconds)
                )
            }
        )


__all__ = [
    "CapabilityHealthEvaluationRequest",
    "CapabilityHealthEvaluationService",
]
