from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ObjectiveRepairExecutionRecord,
)


class ObjectiveRepairExecutionRepository:
    """
    Append-only persistence for one objective-repair planning
    attempt.

    The repository converges duplicate source-event delivery and
    duplicate semantic repair identities onto the same durable
    row. Semantic conflicts are evaluated by the service.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def get_by_id_for_user(
        self,
        *,
        user_id: UUID,
        repair_execution_id: UUID,
    ) -> ObjectiveRepairExecutionRecord | None:
        result = await self.db.execute(
            select(
                ObjectiveRepairExecutionRecord
            ).where(
                ObjectiveRepairExecutionRecord.user_id
                == user_id,
                ObjectiveRepairExecutionRecord.id
                == repair_execution_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user_for_update(
        self,
        *,
        user_id: UUID,
        repair_execution_id: UUID,
    ) -> ObjectiveRepairExecutionRecord | None:
        result = await self.db.execute(
            select(
                ObjectiveRepairExecutionRecord
            )
            .where(
                ObjectiveRepairExecutionRecord.user_id
                == user_id,
                ObjectiveRepairExecutionRecord.id
                == repair_execution_id,
            )
            .with_for_update()
        )

        return result.scalar_one_or_none()

    async def get_by_source_event(
        self,
        *,
        source_event_id: UUID,
    ) -> ObjectiveRepairExecutionRecord | None:
        result = await self.db.execute(
            select(
                ObjectiveRepairExecutionRecord
            ).where(
                ObjectiveRepairExecutionRecord
                .source_event_id
                == source_event_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_semantic_identity(
        self,
        *,
        user_id: UUID,
        resolution_record_id: UUID,
        repair_request_version: int,
        planner_policy_version: int,
        attempt_number: int,
    ) -> ObjectiveRepairExecutionRecord | None:
        result = await self.db.execute(
            select(
                ObjectiveRepairExecutionRecord
            ).where(
                ObjectiveRepairExecutionRecord.user_id
                == user_id,
                ObjectiveRepairExecutionRecord
                .resolution_record_id
                == resolution_record_id,
                ObjectiveRepairExecutionRecord
                .repair_request_version
                == repair_request_version,
                ObjectiveRepairExecutionRecord
                .planner_policy_version
                == planner_policy_version,
                ObjectiveRepairExecutionRecord
                .attempt_number
                == attempt_number,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_request_attempt(
        self,
        *,
        user_id: UUID,
        repair_request_ref: str,
        attempt_number: int,
    ) -> ObjectiveRepairExecutionRecord | None:
        result = await self.db.execute(
            select(
                ObjectiveRepairExecutionRecord
            ).where(
                ObjectiveRepairExecutionRecord.user_id
                == user_id,
                ObjectiveRepairExecutionRecord
                .repair_request_ref
                == repair_request_ref,
                ObjectiveRepairExecutionRecord
                .attempt_number
                == attempt_number,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_resolution(
        self,
        *,
        user_id: UUID,
        resolution_record_id: UUID,
        limit: int = 100,
    ) -> list[ObjectiveRepairExecutionRecord]:
        """
        Return durable repair attempts for one authenticated
        user's exact objective resolution.

        Results are ordered from the earliest semantic repair
        attempt to the latest. Created time and immutable record
        identity provide deterministic tie-breaking for retries
        and concurrent inserts.

        This is a read-only history boundary. It does not lock,
        mutate, transition, launch, publish, or commit.
        """

        if limit < 1 or limit > 500:
            raise ValueError(
                "limit must be between 1 and 500"
            )

        result = await self.db.execute(
            select(
                ObjectiveRepairExecutionRecord
            )
            .where(
                ObjectiveRepairExecutionRecord.user_id
                == user_id,
                ObjectiveRepairExecutionRecord
                .resolution_record_id
                == resolution_record_id,
            )
            .order_by(
                ObjectiveRepairExecutionRecord
                .attempt_number
                .asc(),
                ObjectiveRepairExecutionRecord
                .created_at
                .asc(),
                ObjectiveRepairExecutionRecord
                .id
                .asc(),
            )
            .limit(limit)
        )

        return list(result.scalars().all())

    async def get_latest_for_resolution(
        self,
        *,
        user_id: UUID,
        resolution_record_id: UUID,
    ) -> ObjectiveRepairExecutionRecord | None:
        """
        Return the newest durable repair attempt for one
        authenticated user's objective resolution.

        Ordering is deterministic across retries and concurrent
        inserts. This is a read-only cognitive/query boundary and
        does not lock or mutate the selected repair.
        """

        result = await self.db.execute(
            select(
                ObjectiveRepairExecutionRecord
            )
            .where(
                ObjectiveRepairExecutionRecord.user_id
                == user_id,
                ObjectiveRepairExecutionRecord
                .resolution_record_id
                == resolution_record_id,
            )
            .order_by(
                ObjectiveRepairExecutionRecord
                .attempt_number
                .desc(),
                ObjectiveRepairExecutionRecord
                .created_at
                .desc(),
                ObjectiveRepairExecutionRecord
                .id
                .desc(),
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def record(
        self,
        *,
        values: dict[str, Any],
    ) -> tuple[
        ObjectiveRepairExecutionRecord,
        bool,
    ]:
        statement = (
            insert(ObjectiveRepairExecutionRecord)
            .values(**values)
            .on_conflict_do_nothing()
            .returning(
                ObjectiveRepairExecutionRecord.id
            )
        )

        inserted_id = (
            await self.db.execute(statement)
        ).scalar_one_or_none()

        if inserted_id is not None:
            record = await self.db.get(
                ObjectiveRepairExecutionRecord,
                inserted_id,
            )

            if record is None:
                raise RuntimeError(
                    "Inserted objective repair execution "
                    "could not be reloaded"
                )

            return record, True

        source_event_id = values["source_event_id"]

        existing = await self.get_by_source_event(
            source_event_id=source_event_id,
        )

        if existing is not None:
            return existing, False

        existing = await self.get_by_semantic_identity(
            user_id=values["user_id"],
            resolution_record_id=(
                values["resolution_record_id"]
            ),
            repair_request_version=(
                values["repair_request_version"]
            ),
            planner_policy_version=(
                values["planner_policy_version"]
            ),
            attempt_number=values["attempt_number"],
        )

        if existing is not None:
            return existing, False

        existing = await self.get_by_request_attempt(
            user_id=values["user_id"],
            repair_request_ref=(
                values["repair_request_ref"]
            ),
            attempt_number=values["attempt_number"],
        )

        if existing is not None:
            return existing, False

        raise RuntimeError(
            "Objective repair execution insert conflicted "
            "but no existing row could be resolved"
        )


__all__ = [
    "ObjectiveRepairExecutionRepository",
]
