from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    BusinessLearningObservationRecord,
)
from app.runtime.learning.observations.contracts import (
    BusinessLearningObservation,
)


class BusinessLearningObservationRepository:
    """
    Append-only persistence for normalized business
    learning evidence.

    Projection delivery is idempotent by both source
    evaluation record and source platform event.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def record(
        self,
        *,
        observation: BusinessLearningObservation,
        commit: bool = True,
    ) -> tuple[
        BusinessLearningObservationRecord,
        bool,
    ]:
        values = {
            "id": uuid4(),
            "source_event_id": (
                observation.source_event_id
            ),
            "source_evaluation_record_id": (
                observation
                .source_evaluation_record_id
            ),
            "source_outcome_record_id": (
                observation
                .source_outcome_record_id
            ),
            "user_id": observation.user_id,
            "tenant_id": observation.tenant_id,
            "objective_namespace": (
                observation.objective_namespace
            ),
            "objective_ref": (
                observation.objective_ref
            ),
            "objective_type": (
                observation.objective_type
            ),
            "source_objective_version": (
                observation
                .source_objective_version
            ),
            "outcome_version": (
                observation.outcome_version
            ),
            "evaluation_version": (
                observation.evaluation_version
            ),
            "result": observation.result,
            "reason_code": (
                observation.reason_code
            ),
            "summary": observation.summary,
            "confidence": observation.confidence,
            "retryable": observation.retryable,
            "is_final": observation.is_final,
            "decision": observation.decision,
            "outcome_status": (
                observation.outcome_status
            ),
            "operation_count": (
                observation.operation_count
            ),
            "achieved_operation_count": (
                observation
                .achieved_operation_count
            ),
            "failed_operation_count": (
                observation
                .failed_operation_count
            ),
            "pending_operation_count": (
                observation
                .pending_operation_count
            ),
            "unknown_operation_count": (
                observation
                .unknown_operation_count
            ),
            "not_executed_operation_count": (
                observation
                .not_executed_operation_count
            ),
            "workflow_run_id": (
                observation.workflow_run_id
            ),
            "conversation_id": (
                observation.conversation_id
            ),
            "chat_session_id": (
                observation.chat_session_id
            ),
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
                BusinessLearningObservationRecord
            )
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=[
                    BusinessLearningObservationRecord
                    .source_evaluation_record_id,
                ]
            )
            .returning(
                BusinessLearningObservationRecord.id
            )
        )

        result = await self.db.execute(stmt)
        inserted_id = result.scalar_one_or_none()

        if commit:
            await self.db.commit()
        else:
            await self.db.flush()

        if inserted_id is not None:
            row = await self.get(
                record_id=inserted_id
            )

            if row is None:
                raise RuntimeError(
                    "Inserted business learning "
                    "observation could not be read"
                )

            return row, True

        existing = await (
            self.get_by_evaluation_record(
                source_evaluation_record_id=(
                    observation
                    .source_evaluation_record_id
                )
            )
        )

        if existing is None:
            existing = await self.get_by_source_event(
                source_event_id=(
                    observation.source_event_id
                )
            )

        if existing is None:
            raise RuntimeError(
                "Business learning observation "
                "conflict occurred without an "
                "existing row"
            )

        return existing, False

    async def list_for_aggregation(
        self,
        *,
        user_id: UUID,
        window_hours: int = 720,
        tenant_id: str | None = None,
        objective_namespace: str | None = None,
        objective_type: str | None = None,
        decision: str | None = None,
        now: datetime | None = None,
    ) -> tuple[
        datetime,
        datetime,
        list[BusinessLearningObservationRecord],
    ]:
        if window_hours < 1 or window_hours > 8760:
            raise ValueError(
                "window_hours must be between "
                "1 and 8760"
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
                BusinessLearningObservationRecord
            )
            .where(
                BusinessLearningObservationRecord
                .user_id
                == user_id,
                BusinessLearningObservationRecord
                .observed_at
                >= window_start,
                BusinessLearningObservationRecord
                .observed_at
                < window_end,
            )
            .order_by(
                BusinessLearningObservationRecord
                .observed_at
                .asc(),
                BusinessLearningObservationRecord
                .id
                .asc(),
            )
        )

        filters = (
            (
                BusinessLearningObservationRecord
                .tenant_id,
                tenant_id,
            ),
            (
                BusinessLearningObservationRecord
                .objective_namespace,
                objective_namespace,
            ),
            (
                BusinessLearningObservationRecord
                .objective_type,
                objective_type,
            ),
            (
                BusinessLearningObservationRecord
                .decision,
                decision,
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

    async def get(
        self,
        *,
        record_id: UUID,
    ) -> BusinessLearningObservationRecord | None:
        result = await self.db.execute(
            select(
                BusinessLearningObservationRecord
            ).where(
                BusinessLearningObservationRecord.id
                == record_id
            )
        )

        return result.scalar_one_or_none()

    async def get_for_user(
        self,
        *,
        user_id: UUID,
        record_id: UUID,
    ) -> BusinessLearningObservationRecord | None:
        result = await self.db.execute(
            select(
                BusinessLearningObservationRecord
            ).where(
                BusinessLearningObservationRecord.id
                == record_id,
                BusinessLearningObservationRecord
                .user_id
                == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_by_evaluation_record(
        self,
        *,
        source_evaluation_record_id: UUID,
    ) -> BusinessLearningObservationRecord | None:
        result = await self.db.execute(
            select(
                BusinessLearningObservationRecord
            ).where(
                BusinessLearningObservationRecord
                .source_evaluation_record_id
                == source_evaluation_record_id
            )
        )

        return result.scalar_one_or_none()

    async def get_by_source_event(
        self,
        *,
        source_event_id: UUID,
    ) -> BusinessLearningObservationRecord | None:
        result = await self.db.execute(
            select(
                BusinessLearningObservationRecord
            ).where(
                BusinessLearningObservationRecord
                .source_event_id
                == source_event_id
            )
        )

        return result.scalar_one_or_none()


__all__ = [
    "BusinessLearningObservationRepository",
]
