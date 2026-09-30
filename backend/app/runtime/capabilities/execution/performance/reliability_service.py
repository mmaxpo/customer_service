from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.performance.queries import (
    CapabilityPerformanceQueryRepository,
)
from app.runtime.capabilities.execution.performance.reliability import (
    CapabilityProviderReliabilityReport,
    CapabilityReliabilityPolicy,
)


class CapabilityReliabilityService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        policy: CapabilityReliabilityPolicy | None = None,
    ) -> None:
        self.db = db
        self.repo = CapabilityPerformanceQueryRepository(
            db
        )
        self.policy = (
            policy or CapabilityReliabilityPolicy()
        )

    async def summarize(
        self,
        *,
        user_id,
        window_hours: int = 24,
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        tenant_id: str | None = None,
        now: datetime | None = None,
    ) -> list[CapabilityProviderReliabilityReport]:
        (
            window_start,
            window_end,
            rows,
        ) = await self.repo.summarize(
            user_id=user_id,
            window_hours=window_hours,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
            tenant_id=tenant_id,
            now=now,
        )

        return [
            self._build_report(
                row=row,
                window_start=window_start,
                window_end=window_end,
            )
            for row in rows
        ]

    def _build_report(
        self,
        *,
        row: dict[str, Any],
        window_start: datetime,
        window_end: datetime,
    ) -> CapabilityProviderReliabilityReport:
        attempts = int(row.get("attempts") or 0)
        successes = int(row.get("successes") or 0)
        failures = int(row.get("failures") or 0)
        timeouts = int(row.get("timeouts") or 0)
        provider_errors = int(
            row.get("provider_errors") or 0
        )
        fallback_eligible = int(
            row.get("fallback_eligible_failures") or 0
        )
        fallback_recoveries = int(
            row.get("fallback_recoveries") or 0
        )

        success_rate = (
            successes / attempts
            if attempts
            else 0.0
        )

        recommendation = self.policy.recommend(
            attempts=attempts,
            success_rate=success_rate,
        )

        return CapabilityProviderReliabilityReport(
            capability_id=str(row["capability_id"]),
            provider_id=row.get("provider_id"),
            provider_ref=row.get("provider_ref"),
            tenant_id=row.get("tenant_id"),
            window_start=window_start,
            window_end=window_end,
            attempts=attempts,
            successes=successes,
            failures=failures,
            timeouts=timeouts,
            unavailable=int(row.get("unavailable") or 0),
            circuit_open=int(row.get("circuit_open") or 0),
            provider_errors=provider_errors,
            other_failures=int(
                row.get("other_failures") or 0
            ),
            fallback_eligible_failures=(
                fallback_eligible
            ),
            fallback_recoveries=fallback_recoveries,
            fallback_invocations=int(
                row.get("fallback_invocations") or 0
            ),
            success_rate=success_rate,
            failure_rate=(
                failures / attempts
                if attempts
                else 0.0
            ),
            timeout_rate=(
                timeouts / attempts
                if attempts
                else 0.0
            ),
            provider_error_rate=(
                provider_errors / attempts
                if attempts
                else 0.0
            ),
            fallback_recovery_rate=(
                fallback_recoveries / fallback_eligible
                if fallback_eligible
                else 0.0
            ),
            average_duration_ms=float(
                row.get("average_duration_ms") or 0.0
            ),
            minimum_attempts=self.policy.minimum_attempts,
            evidence_sufficient=(
                attempts >= self.policy.minimum_attempts
            ),
            recommendation=recommendation,
        )


__all__ = ["CapabilityReliabilityService"]
