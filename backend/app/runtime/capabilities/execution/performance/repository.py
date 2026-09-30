from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    CapabilityPerformanceObservationRecord,
)
from app.runtime.capabilities.execution.performance.models import (
    CapabilityPerformanceObservation,
)


class CapabilityPerformanceObservationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_many(
        self,
        *,
        source_event_id: UUID,
        observations: list[CapabilityPerformanceObservation],
    ) -> int:
        if not observations:
            return 0

        values = [
            {
                "id": uuid4(),
                "source_event_id": source_event_id,
                "correlation_id": item.correlation_id,
                "attempt_index": item.attempt_index,
                "requested_capability_id": (
                    item.requested_capability_id
                ),
                "resolved_capability_id": (
                    item.resolved_capability_id
                ),
                "provider_id": item.provider_id,
                "provider_ref": item.provider_ref,
                "status": item.status.value,
                "succeeded": item.succeeded,
                "duration_ms": item.duration_ms,
                "error_code": item.error_code,
                "error_message": item.error_message,
                "failure_kind": item.failure_kind,
                "exception_type": item.exception_type,
                "fallback_allowed": item.fallback_allowed,
                "fallback_used": item.fallback_used,
                "final_attempt": item.final_attempt,
                "health_probe": item.health_probe,
                "health_probe_lease_token": (
                    item.health_probe_lease_token
                ),
                "user_id": item.user_id,
                "tenant_id": item.tenant_id,
                "workflow_run_id": item.workflow_run_id,
                "planner_session_id": item.planner_session_id,
                "thread_id": item.thread_id,
                "observed_at": datetime.fromtimestamp(
                    item.observed_at_ts,
                    tz=timezone.utc,
                ),
                "observation_json": item.model_dump(
                    mode="json"
                ),
            }
            for item in observations
        ]

        stmt = (
            insert(CapabilityPerformanceObservationRecord)
            .values(values)
            .on_conflict_do_nothing(
                index_elements=[
                    CapabilityPerformanceObservationRecord.source_event_id,
                    CapabilityPerformanceObservationRecord.attempt_index,
                ]
            )
            .returning(
                CapabilityPerformanceObservationRecord.id
            )
        )

        result = await self.db.execute(stmt)
        inserted_ids = list(result.scalars().all())
        await self.db.commit()
        return len(inserted_ids)

    async def list_for_event(
        self,
        *,
        source_event_id: UUID,
    ) -> list[CapabilityPerformanceObservationRecord]:
        result = await self.db.execute(
            select(CapabilityPerformanceObservationRecord)
            .where(
                CapabilityPerformanceObservationRecord.source_event_id
                == source_event_id
            )
            .order_by(
                CapabilityPerformanceObservationRecord.attempt_index
            )
        )
        return list(result.scalars().all())

    async def list_for_correlation(
        self,
        *,
        correlation_id: str,
    ) -> list[CapabilityPerformanceObservationRecord]:
        result = await self.db.execute(
            select(CapabilityPerformanceObservationRecord)
            .where(
                CapabilityPerformanceObservationRecord.correlation_id
                == correlation_id
            )
            .order_by(
                CapabilityPerformanceObservationRecord.attempt_index
            )
        )
        return list(result.scalars().all())


__all__ = ["CapabilityPerformanceObservationRepository"]
