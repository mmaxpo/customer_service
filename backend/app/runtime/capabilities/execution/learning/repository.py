from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    CapabilityLearningObservationRecord,
)
from app.runtime.capabilities.execution.learning.contracts import (
    CapabilityLearningObservation,
)


class CapabilityLearningObservationRepository:
    """
    Append-only durable learning evidence.

    Projection delivery is idempotent by both source event and source
    verification record. The repository never updates an existing observation.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def record(
        self,
        *,
        observation: CapabilityLearningObservation,
    ) -> tuple[
        CapabilityLearningObservationRecord,
        bool,
    ]:
        values = {
            "id": uuid4(),
            "source_event_id": (
                observation.source_event_id
            ),
            "source_verification_record_id": (
                observation
                .source_verification_record_id
            ),
            "verification_id": (
                observation.verification_id
            ),
            "attempt_number": (
                observation.attempt_number
            ),
            "user_id": observation.user_id,
            "tenant_id": observation.tenant_id,
            "capability_id": (
                observation.capability_id
            ),
            "provider_id": (
                observation.provider_id
            ),
            "provider_ref": (
                observation.provider_ref
            ),
            "action": observation.action,
            "outcome": observation.outcome,
            "method": observation.method,
            "reason_code": (
                observation.reason_code
            ),
            "confidence": observation.confidence,
            "retryable": observation.retryable,
            "is_final": observation.is_final,
            "correlation_id": (
                observation.correlation_id
            ),
            "workflow_run_id": (
                observation.workflow_run_id
            ),
            "task_id": observation.task_id,
            "summary": observation.summary,
            "observed_outcome_json": dict(
                observation.observed_outcome
            ),
            "evidence_summary_json": dict(
                observation.evidence_summary
            ),
            "context_json": dict(
                observation.context
            ),
            "observed_at": (
                observation.observed_at
            ),
            "observation_json": (
                observation.model_dump(
                    mode="json"
                )
            ),
        }

        stmt = (
            insert(
                CapabilityLearningObservationRecord
            )
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=[
                    CapabilityLearningObservationRecord
                    .source_verification_record_id,
                ]
            )
            .returning(
                CapabilityLearningObservationRecord
                .id
            )
        )

        result = await self.db.execute(stmt)
        inserted_id = result.scalar_one_or_none()
        await self.db.commit()

        if inserted_id is not None:
            row = await self.get(
                record_id=inserted_id
            )

            if row is None:
                raise RuntimeError(
                    "Inserted learning observation "
                    "could not be read"
                )

            return row, True

        existing = await (
            self.get_by_verification_record(
                source_verification_record_id=(
                    observation
                    .source_verification_record_id
                )
            )
        )

        if existing is None:
            raise RuntimeError(
                "Learning observation conflict "
                "occurred without an existing row"
            )

        return existing, False

    async def get(
        self,
        *,
        record_id: UUID,
    ) -> CapabilityLearningObservationRecord | None:
        result = await self.db.execute(
            select(
                CapabilityLearningObservationRecord
            ).where(
                CapabilityLearningObservationRecord
                .id
                == record_id
            )
        )

        return result.scalar_one_or_none()

    async def get_for_user(
        self,
        *,
        user_id: UUID,
        record_id: UUID,
    ) -> CapabilityLearningObservationRecord | None:
        result = await self.db.execute(
            select(
                CapabilityLearningObservationRecord
            ).where(
                CapabilityLearningObservationRecord
                .id
                == record_id,
                CapabilityLearningObservationRecord
                .user_id
                == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_by_verification_record(
        self,
        *,
        source_verification_record_id: UUID,
    ) -> CapabilityLearningObservationRecord | None:
        result = await self.db.execute(
            select(
                CapabilityLearningObservationRecord
            ).where(
                CapabilityLearningObservationRecord
                .source_verification_record_id
                == source_verification_record_id
            )
        )

        return result.scalar_one_or_none()

    async def list_for_aggregation(
        self,
        *,
        user_id: UUID,
        window_hours: int = 720,
        tenant_id: str | None = None,
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        action: str | None = None,
        now: datetime | None = None,
    ) -> tuple[
        datetime,
        datetime,
        list[CapabilityLearningObservationRecord],
    ]:
        if window_hours < 1 or window_hours > 8760:
            raise ValueError(
                "window_hours must be between 1 and 8760"
            )

        window_end = now or datetime.now(
            timezone.utc
        )

        if window_end.tzinfo is None:
            window_end = window_end.replace(
                tzinfo=timezone.utc
            )

        window_start = window_end - timedelta(
            hours=window_hours
        )

        stmt = (
            select(
                CapabilityLearningObservationRecord
            )
            .where(
                CapabilityLearningObservationRecord
                .user_id
                == user_id,
                CapabilityLearningObservationRecord
                .observed_at
                >= window_start,
                CapabilityLearningObservationRecord
                .observed_at
                < window_end,
            )
            .order_by(
                CapabilityLearningObservationRecord
                .observed_at
                .asc(),
                CapabilityLearningObservationRecord
                .id
                .asc(),
            )
        )

        filters = (
            (
                CapabilityLearningObservationRecord
                .tenant_id,
                tenant_id,
            ),
            (
                CapabilityLearningObservationRecord
                .capability_id,
                capability_id,
            ),
            (
                CapabilityLearningObservationRecord
                .provider_id,
                provider_id,
            ),
            (
                CapabilityLearningObservationRecord
                .provider_ref,
                provider_ref,
            ),
            (
                CapabilityLearningObservationRecord
                .action,
                action,
            ),
        )

        for column, value in filters:
            if value is not None:
                stmt = stmt.where(
                    column == value
                )

        result = await self.db.execute(stmt)

        return (
            window_start,
            window_end,
            list(result.scalars().all()),
        )

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None = None,
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        is_final: bool | None = None,
        retryable: bool | None = None,
        correlation_id: str | None = None,
        workflow_run_id: str | None = None,
        task_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[
        CapabilityLearningObservationRecord
    ]:
        if limit < 1 or limit > 500:
            raise ValueError(
                "limit must be between 1 and 500"
            )

        if offset < 0:
            raise ValueError(
                "offset must be >= 0"
            )

        stmt = (
            select(
                CapabilityLearningObservationRecord
            )
            .where(
                CapabilityLearningObservationRecord
                .user_id
                == user_id
            )
            .order_by(
                CapabilityLearningObservationRecord
                .observed_at
                .desc(),
                CapabilityLearningObservationRecord
                .id
                .desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        filters = (
            (
                CapabilityLearningObservationRecord
                .tenant_id,
                tenant_id,
            ),
            (
                CapabilityLearningObservationRecord
                .capability_id,
                capability_id,
            ),
            (
                CapabilityLearningObservationRecord
                .provider_id,
                provider_id,
            ),
            (
                CapabilityLearningObservationRecord
                .provider_ref,
                provider_ref,
            ),
            (
                CapabilityLearningObservationRecord
                .action,
                action,
            ),
            (
                CapabilityLearningObservationRecord
                .outcome,
                outcome,
            ),
            (
                CapabilityLearningObservationRecord
                .correlation_id,
                correlation_id,
            ),
            (
                CapabilityLearningObservationRecord
                .workflow_run_id,
                workflow_run_id,
            ),
            (
                CapabilityLearningObservationRecord
                .task_id,
                task_id,
            ),
        )

        for column, value in filters:
            if value is not None:
                stmt = stmt.where(
                    column == value
                )

        if is_final is not None:
            stmt = stmt.where(
                CapabilityLearningObservationRecord
                .is_final
                == bool(is_final)
            )

        if retryable is not None:
            stmt = stmt.where(
                CapabilityLearningObservationRecord
                .retryable
                == bool(retryable)
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())


__all__ = [
    "CapabilityLearningObservationRepository",
]
