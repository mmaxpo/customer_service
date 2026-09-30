from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.jobs.repository import JobRepository
from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
    build_provider_health_evaluation_key,
    build_provider_health_scope_key,
)
from app.runtime.capabilities.execution.health.scope_repository import (
    CapabilityHealthEvaluationScope,
    CapabilityHealthScopeRepository,
)

HEALTH_EVALUATION_JOB_TYPE = "capability.health.evaluate"


class CapabilityHealthReconcileRequest(BaseModel):
    """
    Configuration for one deterministic reconciliation tick.

    now is supplied explicitly by durable job payloads and tests. The
    reconciler aligns it to the latest completed UTC window.
    """

    model_config = ConfigDict(extra="forbid")

    now: datetime

    window_hours: int = Field(
        default=1,
        ge=1,
        le=8760,
    )
    lookback_windows: int = Field(
        default=24,
        ge=1,
        le=720,
    )
    scope_limit: int = Field(
        default=1000,
        ge=1,
        le=10000,
    )

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

    degrade_after_windows: int = Field(
        default=2,
        ge=1,
    )
    unhealthy_after_windows: int = Field(
        default=3,
        ge=1,
    )
    recover_after_windows: int = Field(
        default=2,
        ge=1,
    )
    cooldown_seconds: int = Field(
        default=300,
        ge=0,
        le=604800,
    )

    def normalized_now(self) -> datetime:
        value = self.now

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)


class CapabilityHealthEvaluationReconciler:
    """
    Reconcile completed health windows into durable evaluation jobs.

    This component never evaluates health inline. It discovers evidence,
    verifies durable decision history, and enqueues the existing worker job.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.scopes = CapabilityHealthScopeRepository(db)
        self.health = CapabilityProviderHealthRepository(db)
        self.jobs = JobRepository(db)

    async def reconcile(
        self,
        *,
        request: CapabilityHealthReconcileRequest,
    ) -> dict[str, Any]:
        now = request.normalized_now()
        completed_window_end = self._completed_window_end(
            now=now,
            window_hours=request.window_hours,
        )
        duration = timedelta(hours=request.window_hours)

        summary: dict[str, Any] = {
            "status": "reconciled",
            "now": now.isoformat(),
            "completed_window_end": (completed_window_end.isoformat()),
            "window_hours": request.window_hours,
            "lookback_windows": (request.lookback_windows),
            "windows_scanned": 0,
            "scopes_discovered": 0,
            "jobs_enqueued": 0,
            "jobs_existing": 0,
            "already_evaluated": 0,
            "errors": [],
            "jobs": [],
        }

        oldest_end = completed_window_end - (duration * (request.lookback_windows - 1))

        for index in range(request.lookback_windows):
            window_end = oldest_end + (duration * index)
            window_start = window_end - duration
            summary["windows_scanned"] += 1

            scopes = await self.scopes.discover_for_window(
                window_start=window_start,
                window_end=window_end,
                limit=request.scope_limit,
            )
            summary["scopes_discovered"] += len(scopes)

            for scope in scopes:
                try:
                    item = await self._enqueue_scope(
                        scope=scope,
                        request=request,
                        window_start=window_start,
                        window_end=window_end,
                    )
                except Exception as exc:
                    summary["errors"].append(
                        {
                            "user_id": str(scope.user_id),
                            "tenant_id": (scope.tenant_id),
                            "capability_id": (scope.capability_id),
                            "provider_id": (scope.provider_id),
                            "provider_ref": (scope.provider_ref),
                            "window_start": (window_start.isoformat()),
                            "window_end": (window_end.isoformat()),
                            "error": str(exc),
                        }
                    )
                    continue

                if item["status"] == ("already_evaluated"):
                    summary["already_evaluated"] += 1
                    continue

                if item["inserted"]:
                    summary["jobs_enqueued"] += 1
                else:
                    summary["jobs_existing"] += 1

                summary["jobs"].append(item)

        if summary["errors"]:
            summary["status"] = "reconciled_with_errors"

        return summary

    async def _enqueue_scope(
        self,
        *,
        scope: CapabilityHealthEvaluationScope,
        request: CapabilityHealthReconcileRequest,
        window_start: datetime,
        window_end: datetime,
    ) -> dict[str, Any]:
        existing_decision = await self.health.get_decision_for_window(
            user_id=scope.user_id,
            tenant_id=scope.tenant_id,
            capability_id=scope.capability_id,
            provider_id=scope.provider_id,
            provider_ref=scope.provider_ref,
            window_start=window_start,
            window_end=window_end,
        )

        if existing_decision is not None:
            return {
                "status": "already_evaluated",
                "evaluation_key": (existing_decision.evaluation_key),
            }

        scope_key = build_provider_health_scope_key(
            user_id=scope.user_id,
            tenant_id=scope.tenant_id,
            capability_id=scope.capability_id,
            provider_id=scope.provider_id,
            provider_ref=scope.provider_ref,
        )
        evaluation_key = build_provider_health_evaluation_key(
            scope_key=scope_key,
            window_start=window_start,
            window_end=window_end,
        )

        payload = {
            "user_id": str(scope.user_id),
            "tenant_id": scope.tenant_id,
            "capability_id": scope.capability_id,
            "provider_id": scope.provider_id,
            "provider_ref": scope.provider_ref,
            "window_hours": (request.window_hours),
            "window_end": window_end.isoformat(),
            "minimum_attempts": (request.minimum_attempts),
            "healthy_success_rate": (request.healthy_success_rate),
            "degraded_success_rate": (request.degraded_success_rate),
            "degrade_after_windows": (request.degrade_after_windows),
            "unhealthy_after_windows": (request.unhealthy_after_windows),
            "recover_after_windows": (request.recover_after_windows),
            "cooldown_seconds": (request.cooldown_seconds),
        }

        before = await self._get_job(
            evaluation_key=evaluation_key,
        )

        job = await self.jobs.enqueue(
            user_id=scope.user_id,
            job_type=HEALTH_EVALUATION_JOB_TYPE,
            payload=payload,
            max_attempts=5,
            idempotency_key=evaluation_key,
        )

        return {
            "status": "enqueued",
            "inserted": before is None,
            "job_id": str(job.id),
            "job_status": job.status,
            "evaluation_key": evaluation_key,
            "user_id": str(scope.user_id),
            "tenant_id": scope.tenant_id,
            "capability_id": scope.capability_id,
            "provider_id": scope.provider_id,
            "provider_ref": scope.provider_ref,
            "window_start": (window_start.isoformat()),
            "window_end": window_end.isoformat(),
        }

    async def _get_job(
        self,
        *,
        evaluation_key: str,
    ):
        from sqlalchemy import select

        from app.models.models import PlatformJob

        result = await self.db.execute(
            select(PlatformJob).where(
                PlatformJob.job_type == HEALTH_EVALUATION_JOB_TYPE,
                PlatformJob.idempotency_key == evaluation_key,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _completed_window_end(
        *,
        now: datetime,
        window_hours: int,
    ) -> datetime:
        seconds = window_hours * 3600
        timestamp = int(now.timestamp())
        aligned = timestamp - (timestamp % seconds)
        return datetime.fromtimestamp(
            aligned,
            tz=timezone.utc,
        )


__all__ = [
    "CapabilityHealthEvaluationReconciler",
    "CapabilityHealthReconcileRequest",
    "HEALTH_EVALUATION_JOB_TYPE",
]
