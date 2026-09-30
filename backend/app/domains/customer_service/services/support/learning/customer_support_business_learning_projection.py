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
from app.domains.customer_service.services.support.learning.customer_support_business_learning import (
    CustomerSupportBusinessLearningMapper,
)
from app.runtime.learning import (
    BusinessLearningObservationRepository,
)


SUPPORT_OUTCOME_EVALUATED_EVENT = (
    "customer_service.support.outcome.evaluated"
)


class CustomerSupportBusinessLearningProjector:
    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: (
            BusinessLearningObservationRepository
            | None
        ) = None,
        mapper: (
            CustomerSupportBusinessLearningMapper
            | None
        ) = None,
    ) -> None:
        self.db = db
        self.repository = (
            repository
            or BusinessLearningObservationRepository(
                db
            )
        )
        self.mapper = (
            mapper
            or CustomerSupportBusinessLearningMapper()
        )

    async def project_event(
        self,
        event: Any,
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        if (
            event.event_type
            != SUPPORT_OUTCOME_EVALUATED_EVENT
        ):
            raise ValueError(
                "Unexpected business learning source "
                f"event type: {event.event_type}"
            )

        if event.user_id is None:
            raise ValueError(
                "Business learning event user_id "
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
                "Business learning event "
                "evaluation_id is required"
            )

        if not raw_outcome_id:
            raise ValueError(
                "Business learning event "
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
                "found for business learning event"
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
                "business learning event"
            )

        observation = self.mapper.build(
            event=event,
            outcome=outcome,
            evaluation=evaluation,
        )

        row, inserted = await (
            self.repository.record(
                observation=observation,
                commit=commit,
            )
        )

        return {
            "source_event_id": str(event.id),
            "source_evaluation_record_id": str(
                evaluation.id
            ),
            "source_outcome_record_id": str(
                outcome.id
            ),
            "business_learning_observation_id": (
                str(row.id)
            ),
            "objective_namespace": (
                row.objective_namespace
            ),
            "objective_ref": row.objective_ref,
            "result": row.result,
            "is_final": row.is_final,
            "inserted": inserted,
        }


__all__ = [
    "CustomerSupportBusinessLearningProjector",
    "SUPPORT_OUTCOME_EVALUATED_EVENT",
]
