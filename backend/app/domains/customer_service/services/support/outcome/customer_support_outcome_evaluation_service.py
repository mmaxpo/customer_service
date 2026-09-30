from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models.outcomes import (
    CustomerSupportOutcomeEvaluationRecord,
)
from app.domains.customer_service.repositories.customer_support_outcome_evaluations import (
    CustomerSupportOutcomeEvaluationRepository,
)
from app.domains.customer_service.repositories.customer_support_outcomes import (
    CustomerSupportOutcomeRepository,
)
from app.domains.customer_service.services.support.outcome.customer_support_outcome_evaluation import (
    CustomerSupportOutcomeEvaluator,
)
from app.platform.events.publisher import (
    PlatformEventPublisher,
)


SUPPORT_OUTCOME_EVALUATED_EVENT = (
    "customer_service.support.outcome.evaluated"
)


@dataclass(frozen=True)
class CustomerSupportOutcomeEvaluationExecution:
    record: CustomerSupportOutcomeEvaluationRecord
    created: bool
    event_id: UUID | None


class CustomerSupportOutcomeEvaluationService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        evaluator: (
            CustomerSupportOutcomeEvaluator | None
        ) = None,
    ) -> None:
        self.db = db
        self.evaluator = (
            evaluator
            or CustomerSupportOutcomeEvaluator()
        )
        self.outcomes = (
            CustomerSupportOutcomeRepository(db)
        )
        self.evaluations = (
            CustomerSupportOutcomeEvaluationRepository(
                db
            )
        )

    async def evaluate(
        self,
        *,
        user_id: UUID,
        support_outcome_id: UUID,
    ) -> CustomerSupportOutcomeEvaluationExecution:
        outcome = await self.outcomes.get_for_user(
            user_id=user_id,
            outcome_id=support_outcome_id,
        )

        if outcome is None:
            raise ValueError(
                "Support outcome was not found for user"
            )

        evaluation = self.evaluator.evaluate(
            outcome
        )

        write = await self.evaluations.record_once(
            values={
                "user_id": user_id,
                "support_outcome_id": outcome.id,
                "review_plan_id": (
                    outcome.review_plan_id
                ),
                "workflow_run_id": (
                    outcome.workflow_run_id
                ),
                "evaluation_version": (
                    evaluation.evaluation_version
                ),
                "result": (
                    evaluation.result.value
                ),
                "reason_code": (
                    evaluation.reason_code
                ),
                "summary": evaluation.summary,
                "confidence": (
                    evaluation.confidence
                ),
                "retryable": (
                    evaluation.retryable
                ),
                "achieved_operation_count": (
                    evaluation
                    .achieved_operation_count
                ),
                "failed_operation_count": (
                    evaluation
                    .failed_operation_count
                ),
                "pending_operation_count": (
                    evaluation
                    .pending_operation_count
                ),
                "unknown_operation_count": (
                    evaluation
                    .unknown_operation_count
                ),
                "not_executed_operation_count": (
                    evaluation
                    .not_executed_operation_count
                ),
                "observed_outcome_json": (
                    evaluation.observed_outcome
                ),
                "evidence_json": (
                    evaluation.evidence
                ),
            }
        )

        event_id = None

        if write.created:
            published = await (
                PlatformEventPublisher(
                    self.db
                ).publish(
                    user_id=user_id,
                    event_type=(
                        SUPPORT_OUTCOME_EVALUATED_EVENT
                    ),
                    source=(
                        "customer_service."
                        "support_outcome_evaluation"
                    ),
                    payload={
                        "evaluation_id": str(
                            write.record.id
                        ),
                        "support_outcome_id": str(
                            outcome.id
                        ),
                        "review_plan_id": (
                            outcome.review_plan_id
                        ),
                        "evaluation_version": (
                            evaluation
                            .evaluation_version
                        ),
                        "result": (
                            evaluation.result.value
                        ),
                        "reason_code": (
                            evaluation.reason_code
                        ),
                        "confidence": (
                            evaluation.confidence
                        ),
                        "retryable": (
                            evaluation.retryable
                        ),
                    },
                    meta={
                        "workflow_run_id": str(
                            outcome.workflow_run_id
                        ),
                        "conversation_id": str(
                            outcome.conversation_id
                        ),
                    },
                    dispatch=True,
                    commit=False,
                )
            )

            event_id = published["event"].id

        await self.db.commit()
        await self.db.refresh(write.record)

        return (
            CustomerSupportOutcomeEvaluationExecution(
                record=write.record,
                created=write.created,
                event_id=event_id,
            )
        )


__all__ = [
    "CustomerSupportOutcomeEvaluationExecution",
    "CustomerSupportOutcomeEvaluationService",
    "SUPPORT_OUTCOME_EVALUATED_EVENT",
]
