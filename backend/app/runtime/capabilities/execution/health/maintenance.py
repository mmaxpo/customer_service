from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.jobs.repository import JobRepository

CAPABILITY_HEALTH_RECONCILE_JOB_TYPE = "capability.health.reconcile"
CAPABILITY_HEALTH_MAINTENANCE_KEY_PREFIX = "capability-health-reconcile:v1"


class CapabilityHealthMaintenanceTicker:
    """
    Enqueue one durable health-reconciliation job per completed UTC bucket.

    Every worker process may call tick(). PlatformJob's unique constraint on
    (job_type, idempotency_key) elects one durable job without requiring an
    application-level leader or a permanent schedule row.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        window_hours: int = 1,
        lookback_windows: int = 24,
        scope_limit: int = 1000,
        key_prefix: str = (CAPABILITY_HEALTH_MAINTENANCE_KEY_PREFIX),
    ) -> None:
        if window_hours < 1:
            raise ValueError("window_hours must be >= 1")
        if lookback_windows < 1:
            raise ValueError("lookback_windows must be >= 1")
        if scope_limit < 1:
            raise ValueError("scope_limit must be >= 1")

        normalized_prefix = str(key_prefix or "").strip()

        if not normalized_prefix:
            raise ValueError("key_prefix cannot be empty")

        self.db = db
        self.jobs = JobRepository(db)
        self.window_hours = window_hours
        self.lookback_windows = lookback_windows
        self.scope_limit = scope_limit
        self.key_prefix = normalized_prefix

    async def tick(
        self,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        observed_at = self._normalize_datetime(now)
        bucket = self.align_bucket(
            now=observed_at,
            window_hours=self.window_hours,
        )
        idempotency_key = self.build_idempotency_key(bucket)

        job = await self.jobs.enqueue(
            user_id=None,
            job_type=(CAPABILITY_HEALTH_RECONCILE_JOB_TYPE),
            payload={
                "now": observed_at.isoformat(),
                "window_hours": self.window_hours,
                "lookback_windows": (self.lookback_windows),
                "scope_limit": self.scope_limit,
                "maintenance_bucket": (bucket.isoformat()),
                "maintenance_source": ("job_worker_runner"),
            },
            max_attempts=5,
            idempotency_key=idempotency_key,
        )

        return {
            "status": "enqueued_or_existing",
            "job_id": str(job.id),
            "job_status": job.status,
            "job_type": job.job_type,
            "idempotency_key": idempotency_key,
            "maintenance_bucket": (bucket.isoformat()),
            "observed_at": (observed_at.isoformat()),
        }

    def build_idempotency_key(
        self,
        bucket: datetime,
    ) -> str:
        normalized = self._normalize_datetime(bucket)

        return f"{self.key_prefix}:{normalized.isoformat()}"

    @staticmethod
    def align_bucket(
        *,
        now: datetime,
        window_hours: int,
    ) -> datetime:
        if window_hours < 1:
            raise ValueError("window_hours must be >= 1")

        normalized = CapabilityHealthMaintenanceTicker._normalize_datetime(now)
        seconds = window_hours * 3600
        timestamp = int(normalized.timestamp())
        aligned = timestamp - (timestamp % seconds)

        return datetime.fromtimestamp(
            aligned,
            tz=timezone.utc,
        )

    @staticmethod
    def _normalize_datetime(
        value: datetime | None,
    ) -> datetime:
        result = value or datetime.now(timezone.utc)

        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)

        return result.astimezone(timezone.utc)


__all__ = [
    "CAPABILITY_HEALTH_MAINTENANCE_KEY_PREFIX",
    "CAPABILITY_HEALTH_RECONCILE_JOB_TYPE",
    "CapabilityHealthMaintenanceTicker",
]
