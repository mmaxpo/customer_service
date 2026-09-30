from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ObjectiveResolutionRecord,
)
from app.platform.events.publisher import (
    PlatformEventPublisher,
)
from app.runtime.objectives.resolution.contracts import (
    ObjectiveResolutionAssessment,
)
from app.runtime.objectives.resolution.repository import (
    ObjectiveResolutionRepository,
)


OBJECTIVE_RESOLUTION_ASSESSED_EVENT = (
    "runtime.objective.resolution.assessed"
)

OBJECTIVE_RESOLUTION_EVENT_SOURCE = (
    "runtime.objective_resolution"
)


@dataclass(frozen=True)
class ObjectiveResolutionExecution:
    record: ObjectiveResolutionRecord
    created: bool
    event_id: UUID | None


class ObjectiveResolutionService:
    """
    Persist one normalized assessment and publish its
    secret-minimizing lifecycle event atomically.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: (
            ObjectiveResolutionRepository | None
        ) = None,
    ) -> None:
        self.db = db
        self.repository = (
            repository
            or ObjectiveResolutionRepository(db)
        )

    async def record_assessment(
        self,
        *,
        source_event_id: UUID,
        user_id: UUID,
        tenant_id: str | None,
        assessment: ObjectiveResolutionAssessment,
        projection_version: int = 1,
    ) -> ObjectiveResolutionExecution:
        try:
            record, created = await (
                self.repository.record(
                    source_event_id=source_event_id,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    assessment=assessment,
                    projection_version=(
                        projection_version
                    ),
                    commit=False,
                )
            )

            event_id = None

            if created:
                published = await (
                    PlatformEventPublisher(
                        self.db
                    ).publish(
                        user_id=user_id,
                        event_type=(
                            OBJECTIVE_RESOLUTION_ASSESSED_EVENT
                        ),
                        source=(
                            OBJECTIVE_RESOLUTION_EVENT_SOURCE
                        ),
                        payload={
                            "resolution_record_id": (
                                str(record.id)
                            ),
                            "objective_namespace": (
                                record
                                .objective_namespace
                            ),
                            "objective_type": (
                                record.objective_type
                            ),
                            "objective_ref": (
                                record.objective_ref
                            ),
                            "objective_version": (
                                record
                                .objective_version
                            ),
                            "source_outcome_ref": (
                                record
                                .source_outcome_ref
                            ),
                            "outcome_version": (
                                record.outcome_version
                            ),
                            "source_evaluation_ref": (
                                record
                                .source_evaluation_ref
                            ),
                            "evaluation_version": (
                                record
                                .evaluation_version
                            ),
                            "projection_version": (
                                record
                                .projection_version
                            ),
                            "status": record.status,
                            "reason_code": (
                                record.reason_code
                            ),
                            "confidence": (
                                record.confidence
                            ),
                            "is_terminal": (
                                record.is_terminal
                            ),
                            "operation_count": (
                                record.operation_count
                            ),
                            "unresolved_operation_count": (
                                record
                                .unresolved_operation_count
                            ),
                        },
                        meta={
                            "tenant_id": tenant_id,
                            "workflow_run_id": (
                                record.workflow_run_id
                            ),
                        },
                        dispatch=True,
                        commit=False,
                    )
                )

                event_id = published["event"].id

            await self.db.commit()
            await self.db.refresh(record)

            return ObjectiveResolutionExecution(
                record=record,
                created=created,
                event_id=event_id,
            )
        except Exception:
            await self.db.rollback()
            raise


__all__ = [
    "OBJECTIVE_RESOLUTION_ASSESSED_EVENT",
    "OBJECTIVE_RESOLUTION_EVENT_SOURCE",
    "ObjectiveResolutionExecution",
    "ObjectiveResolutionService",
]
