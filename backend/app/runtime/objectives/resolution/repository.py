from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ObjectiveResolutionRecord,
)
from app.runtime.objectives.resolution.contracts import (
    ObjectiveResolutionAssessment,
)


class ObjectiveResolutionConflictError(
    RuntimeError
):
    pass


def normalize_resolution_user_id(
    value,
) -> UUID:
    if isinstance(value, UUID):
        return value

    try:
        return UUID(str(value))
    except (
        TypeError,
        ValueError,
        AttributeError,
    ) as exc:
        raise ValueError(
            "user_id must be a valid UUID"
        ) from exc


def normalize_projection_version(
    value,
) -> int:
    try:
        normalized = int(value)
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "projection_version must be an integer"
        ) from exc

    if normalized < 1:
        raise ValueError(
            "projection_version must be >= 1"
        )

    return normalized


class ObjectiveResolutionRepository:
    """
    Append-only objective-resolution persistence.

    A projection is idempotent by both source event and
    semantic source evaluation identity.

    Writes flush but do not commit unless requested. This
    allows record and lifecycle event creation to share one
    transaction.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def record(
        self,
        *,
        source_event_id: UUID,
        user_id: UUID | str,
        tenant_id: str | None,
        assessment: ObjectiveResolutionAssessment,
        projection_version: int = 1,
        commit: bool = False,
    ) -> tuple[
        ObjectiveResolutionRecord,
        bool,
    ]:
        normalized_user_id = (
            normalize_resolution_user_id(user_id)
        )
        normalized_projection_version = (
            normalize_projection_version(
                projection_version
            )
        )

        serialized = assessment.model_dump(
            mode="json"
        )

        values = {
            "id": uuid4(),
            "source_event_id": source_event_id,
            "user_id": normalized_user_id,
            "tenant_id": (
                str(tenant_id).strip()
                if tenant_id is not None
                and str(tenant_id).strip()
                else None
            ),
            "objective_namespace": (
                assessment.objective.namespace
            ),
            "objective_type": (
                assessment.objective.objective_type
            ),
            "objective_ref": (
                assessment.objective.objective_ref
            ),
            "objective_version": (
                assessment.objective
                .objective_version
            ),
            "source_outcome_ref": (
                assessment.source.outcome_ref
            ),
            "outcome_version": (
                assessment.source.outcome_version
            ),
            "source_evaluation_ref": (
                assessment.source.evaluation_ref
            ),
            "evaluation_version": (
                assessment.source
                .evaluation_version
            ),
            "projection_version": (
                normalized_projection_version
            ),
            "assessment_schema_version": (
                assessment.schema_version
            ),
            "workflow_run_id": (
                assessment.source.workflow_run_id
            ),
            "status": assessment.status.value,
            "reason_code": assessment.reason_code,
            "summary": assessment.summary,
            "confidence": assessment.confidence,
            "is_terminal": (
                assessment.is_terminal
            ),
            "operation_count": len(
                assessment.operations
            ),
            "achieved_operation_count": len(
                assessment
                .achieved_operation_refs
            ),
            "unresolved_operation_count": len(
                assessment
                .unresolved_operation_refs
            ),
            "failed_operation_count": len(
                assessment.failed_operation_refs
            ),
            "pending_operation_count": len(
                assessment.pending_operation_refs
            ),
            "unknown_operation_count": len(
                assessment.unknown_operation_refs
            ),
            "not_executed_operation_count": len(
                assessment
                .not_executed_operation_refs
            ),
            "assessment_json": serialized,
        }

        stmt = (
            insert(ObjectiveResolutionRecord)
            .values(**values)
            # Either durable identity may conflict:
            #
            # 1. the same platform event is delivered again;
            # 2. another equivalent event references the same
            #    source evaluation and projection version.
            #
            # Omitting a conflict target allows both unique
            # constraints to converge safely. The repository
            # resolves the existing row below and verifies that
            # its assessment facts are identical.
            .on_conflict_do_nothing()
            .returning(
                ObjectiveResolutionRecord.id
            )
        )

        result = await self.db.execute(stmt)
        inserted_id = result.scalar_one_or_none()

        if commit:
            await self.db.commit()
        else:
            await self.db.flush()

        if inserted_id is not None:
            created = await self.get(
                record_id=inserted_id
            )

            if created is None:
                raise RuntimeError(
                    "Inserted objective resolution "
                    "record could not be read"
                )

            return created, True

        existing = await self.get_by_source_event(
            source_event_id=source_event_id
        )

        if existing is None:
            existing = await (
                self.get_by_source_evaluation(
                    user_id=normalized_user_id,
                    objective_namespace=(
                        assessment.objective
                        .namespace
                    ),
                    source_evaluation_ref=(
                        assessment.source
                        .evaluation_ref
                    ),
                    evaluation_version=(
                        assessment.source
                        .evaluation_version
                    ),
                    projection_version=(
                        normalized_projection_version
                    ),
                )
            )

        if existing is None:
            raise RuntimeError(
                "Objective resolution conflict "
                "occurred without an existing row"
            )

        self._assert_same_projection(
            existing=existing,
            assessment_json=serialized,
            projection_version=(
                normalized_projection_version
            ),
        )

        return existing, False

    async def get(
        self,
        *,
        record_id: UUID,
    ) -> ObjectiveResolutionRecord | None:
        result = await self.db.execute(
            select(
                ObjectiveResolutionRecord
            ).where(
                ObjectiveResolutionRecord.id
                == record_id
            )
        )
        return result.scalar_one_or_none()

    async def get_for_user(
        self,
        *,
        user_id: UUID | str,
        record_id: UUID,
    ) -> ObjectiveResolutionRecord | None:
        normalized_user_id = (
            normalize_resolution_user_id(user_id)
        )

        result = await self.db.execute(
            select(
                ObjectiveResolutionRecord
            ).where(
                ObjectiveResolutionRecord.id
                == record_id,
                ObjectiveResolutionRecord.user_id
                == normalized_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_source_event(
        self,
        *,
        source_event_id: UUID,
    ) -> ObjectiveResolutionRecord | None:
        result = await self.db.execute(
            select(
                ObjectiveResolutionRecord
            ).where(
                ObjectiveResolutionRecord
                .source_event_id
                == source_event_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_source_evaluation(
        self,
        *,
        user_id: UUID | str,
        objective_namespace: str,
        source_evaluation_ref: str,
        evaluation_version: int,
        projection_version: int,
    ) -> ObjectiveResolutionRecord | None:
        normalized_user_id = (
            normalize_resolution_user_id(user_id)
        )

        result = await self.db.execute(
            select(
                ObjectiveResolutionRecord
            ).where(
                ObjectiveResolutionRecord.user_id
                == normalized_user_id,
                ObjectiveResolutionRecord
                .objective_namespace
                == str(
                    objective_namespace
                ).strip().lower(),
                ObjectiveResolutionRecord
                .source_evaluation_ref
                == str(
                    source_evaluation_ref
                ).strip(),
                ObjectiveResolutionRecord
                .evaluation_version
                == int(evaluation_version),
                ObjectiveResolutionRecord
                .projection_version
                == int(projection_version),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_objective(
        self,
        *,
        user_id: UUID | str,
        objective_namespace: str,
        objective_ref: str,
        limit: int = 100,
    ) -> list[ObjectiveResolutionRecord]:
        normalized_user_id = (
            normalize_resolution_user_id(user_id)
        )

        if limit < 1 or limit > 500:
            raise ValueError(
                "limit must be between 1 and 500"
            )

        result = await self.db.execute(
            select(
                ObjectiveResolutionRecord
            )
            .where(
                ObjectiveResolutionRecord.user_id
                == normalized_user_id,
                ObjectiveResolutionRecord
                .objective_namespace
                == str(
                    objective_namespace
                ).strip().lower(),
                ObjectiveResolutionRecord
                .objective_ref
                == str(objective_ref).strip(),
            )
            .order_by(
                ObjectiveResolutionRecord
                .objective_version
                .asc(),
                ObjectiveResolutionRecord
                .outcome_version
                .asc(),
                ObjectiveResolutionRecord
                .evaluation_version
                .asc(),
                ObjectiveResolutionRecord
                .projection_version
                .asc(),
                ObjectiveResolutionRecord
                .created_at
                .asc(),
                ObjectiveResolutionRecord.id
                .asc(),
            )
            .limit(limit)
        )

        return list(result.scalars().all())

    async def get_latest_for_objective(
        self,
        *,
        user_id: UUID | str,
        objective_namespace: str,
        objective_ref: str,
    ) -> ObjectiveResolutionRecord | None:
        normalized_user_id = (
            normalize_resolution_user_id(user_id)
        )

        result = await self.db.execute(
            select(
                ObjectiveResolutionRecord
            )
            .where(
                ObjectiveResolutionRecord.user_id
                == normalized_user_id,
                ObjectiveResolutionRecord
                .objective_namespace
                == str(
                    objective_namespace
                ).strip().lower(),
                ObjectiveResolutionRecord
                .objective_ref
                == str(objective_ref).strip(),
            )
            .order_by(
                ObjectiveResolutionRecord
                .objective_version
                .desc(),
                ObjectiveResolutionRecord
                .outcome_version
                .desc(),
                ObjectiveResolutionRecord
                .evaluation_version
                .desc(),
                ObjectiveResolutionRecord
                .projection_version
                .desc(),
                ObjectiveResolutionRecord
                .created_at
                .desc(),
                ObjectiveResolutionRecord.id
                .desc(),
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    @staticmethod
    def assessment_from_record(
        record: ObjectiveResolutionRecord,
    ) -> ObjectiveResolutionAssessment:
        return (
            ObjectiveResolutionAssessment
            .model_validate(
                dict(
                    record.assessment_json
                    or {}
                )
            )
        )

    @staticmethod
    def _assert_same_projection(
        *,
        existing: ObjectiveResolutionRecord,
        assessment_json: dict,
        projection_version: int,
    ) -> None:
        if (
            existing.projection_version
            != projection_version
            or dict(
                existing.assessment_json
                or {}
            )
            != assessment_json
        ):
            raise ObjectiveResolutionConflictError(
                "Objective resolution source "
                "identity already exists with "
                "different assessment facts"
            )


__all__ = [
    "ObjectiveResolutionConflictError",
    "ObjectiveResolutionRepository",
    "normalize_projection_version",
    "normalize_resolution_user_id",
]
