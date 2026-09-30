from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.customer_support_outcome_evaluations import (
    CustomerSupportOutcomeEvaluationRepository,
)
from app.domains.customer_service.repositories.customer_support_outcomes import (
    CustomerSupportOutcomeRepository,
)
from app.domains.customer_service.services.support.resolution.customer_support_resolution_assessment import (
    CustomerSupportResolutionAssessmentAdapter,
)
from app.runtime.objectives.resolution import (
    ObjectiveResolutionContext,
    ObjectiveResolutionService,
)


SUPPORT_OUTCOME_EVALUATED_EVENT = (
    "customer_service.support.outcome.evaluated"
)

CUSTOMER_SUPPORT_RESOLUTION_PROJECTION_VERSION = 1


class CustomerSupportResolutionProjector:
    """
    Product-owned loader and adapter for projecting a
    customer-support evaluation into generic durable
    objective-resolution truth.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        adapter: (
            CustomerSupportResolutionAssessmentAdapter
            | None
        ) = None,
        resolution_service: (
            ObjectiveResolutionService | None
        ) = None,
    ) -> None:
        self.db = db
        self.adapter = (
            adapter
            or CustomerSupportResolutionAssessmentAdapter()
        )
        self.resolution_service = (
            resolution_service
            or ObjectiveResolutionService(db)
        )

    async def project_event(
        self,
        event: Any,
        *,
        projection_version: int = (
            CUSTOMER_SUPPORT_RESOLUTION_PROJECTION_VERSION
        ),
    ):
        if (
            event.event_type
            != SUPPORT_OUTCOME_EVALUATED_EVENT
        ):
            raise ValueError(
                "Unexpected objective-resolution "
                f"source event type: {event.event_type}"
            )

        if event.user_id is None:
            raise ValueError(
                "Objective-resolution event user_id "
                "is required"
            )

        payload = dict(event.payload or {})

        raw_evaluation_id = payload.get(
            "evaluation_id"
        )
        raw_outcome_id = payload.get(
            "support_outcome_id"
        )

        if not raw_evaluation_id:
            raise ValueError(
                "Objective-resolution event "
                "evaluation_id is required"
            )

        if not raw_outcome_id:
            raise ValueError(
                "Objective-resolution event "
                "support_outcome_id is required"
            )

        user_id = UUID(str(event.user_id))
        evaluation_id = UUID(
            str(raw_evaluation_id)
        )
        outcome_id = UUID(
            str(raw_outcome_id)
        )

        evaluation = await (
            CustomerSupportOutcomeEvaluationRepository(
                self.db
            ).get(
                user_id=user_id,
                evaluation_id=evaluation_id,
            )
        )

        if evaluation is None:
            raise ValueError(
                "Support outcome evaluation was not "
                "found for objective-resolution event"
            )

        outcome = await (
            CustomerSupportOutcomeRepository(
                self.db
            ).get_for_user(
                user_id=user_id,
                outcome_id=outcome_id,
            )
        )

        if outcome is None:
            raise ValueError(
                "Support outcome was not found for "
                "objective-resolution event"
            )

        if (
            evaluation.support_outcome_id
            != outcome.id
        ):
            raise ValueError(
                "Support evaluation does not reference "
                "the source outcome"
            )

        if (
            evaluation.review_plan_id
            != outcome.review_plan_id
        ):
            raise ValueError(
                "Support evaluation review plan does "
                "not match the source outcome"
            )

        assessment = self.adapter.assess(
            ObjectiveResolutionContext(
                outcome=outcome,
                evaluation=evaluation,
                metadata={
                    "source_event_id": str(event.id),
                },
            )
        )

        if (
            assessment.source.evaluation_ref
            != str(evaluation.id)
        ):
            raise ValueError(
                "Resolution assessment evaluation "
                "identity does not match source record"
            )

        if (
            assessment.source.outcome_ref
            != str(outcome.id)
        ):
            raise ValueError(
                "Resolution assessment outcome identity "
                "does not match source record"
            )

        return await (
            self.resolution_service
            .record_assessment(
                source_event_id=event.id,
                user_id=user_id,
                tenant_id=None,
                assessment=assessment,
                projection_version=(
                    projection_version
                ),
            )
        )


__all__ = [
    "CUSTOMER_SUPPORT_RESOLUTION_PROJECTION_VERSION",
    "CustomerSupportResolutionProjector",
    "SUPPORT_OUTCOME_EVALUATED_EVENT",
]
