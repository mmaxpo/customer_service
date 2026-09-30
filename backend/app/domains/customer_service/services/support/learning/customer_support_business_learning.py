from __future__ import annotations

from typing import Any

from app.runtime.learning import (
    BusinessLearningObservation,
)


class CustomerSupportBusinessLearningMapper:
    """
    Convert a canonical customer-support outcome and
    its deterministic evaluation into generic business
    learning evidence.

    Raw operation payloads and evidence data are not
    copied into the observation.
    """

    def build(
        self,
        *,
        event: Any,
        outcome: Any,
        evaluation: Any,
    ) -> BusinessLearningObservation:
        self._validate_ownership(
            event=event,
            outcome=outcome,
            evaluation=evaluation,
        )

        evidence = list(
            evaluation.evidence_json or []
        )

        evidence_summary = {
            "count": len(evidence),
            "items": [
                {
                    "kind": item.get("kind"),
                    "source": item.get("source"),
                }
                for item in evidence
                if isinstance(item, dict)
            ],
        }

        context = {
            "business_domain": (
                "customer_service"
            ),
            "source_type": (
                "customer_support_outcome"
            ),
            "review_plan_id": (
                outcome.review_plan_id
            ),
            "order_ref": outcome.order_ref,
            "customer_message_present": bool(
                str(
                    outcome.customer_message
                    or ""
                ).strip()
            ),
        }

        return BusinessLearningObservation(
            source_event_id=event.id,
            source_evaluation_record_id=(
                evaluation.id
            ),
            source_outcome_record_id=(
                outcome.id
            ),
            user_id=outcome.user_id,
            tenant_id=None,
            objective_namespace=(
                outcome.objective_namespace
            ),
            objective_ref=(
                outcome.objective_ref
            ),
            objective_type=(
                outcome.objective_type
            ),
            source_objective_version=(
                outcome.source_objective_version
            ),
            outcome_version=(
                outcome.outcome_version
            ),
            evaluation_version=(
                evaluation.evaluation_version
            ),
            result=evaluation.result,
            reason_code=(
                evaluation.reason_code
            ),
            summary=evaluation.summary,
            confidence=evaluation.confidence,
            retryable=evaluation.retryable,
            is_final=not bool(
                evaluation.retryable
            ),
            decision=outcome.decision,
            outcome_status=outcome.status,
            operation_count=(
                outcome.operation_count
            ),
            achieved_operation_count=(
                evaluation
                .achieved_operation_count
            ),
            failed_operation_count=(
                evaluation
                .failed_operation_count
            ),
            pending_operation_count=(
                evaluation
                .pending_operation_count
            ),
            unknown_operation_count=(
                evaluation
                .unknown_operation_count
            ),
            not_executed_operation_count=(
                evaluation
                .not_executed_operation_count
            ),
            workflow_run_id=str(
                outcome.workflow_run_id
            ),
            conversation_id=str(
                outcome.conversation_id
            ),
            chat_session_id=str(
                outcome.chat_session_id
            ),
            observed_outcome=dict(
                evaluation
                .observed_outcome_json
                or {}
            ),
            evidence_summary=(
                evidence_summary
            ),
            context=context,
            observed_at=(
                evaluation.created_at
            ),
        )

    @staticmethod
    def _validate_ownership(
        *,
        event: Any,
        outcome: Any,
        evaluation: Any,
    ) -> None:
        if event.user_id is None:
            raise ValueError(
                "Business learning event user_id "
                "is required"
            )

        identities = {
            str(event.user_id),
            str(outcome.user_id),
            str(evaluation.user_id),
        }

        if len(identities) != 1:
            raise ValueError(
                "Business learning source ownership "
                "does not match"
            )

        if (
            evaluation.support_outcome_id
            != outcome.id
        ):
            raise ValueError(
                "Business learning evaluation does "
                "not reference the supplied outcome"
            )

        payload = dict(event.payload or {})

        raw_evaluation_id = payload.get(
            "evaluation_id"
        )
        raw_outcome_id = payload.get(
            "support_outcome_id"
        )

        if (
            not raw_evaluation_id
            or str(raw_evaluation_id)
            != str(evaluation.id)
        ):
            raise ValueError(
                "Business learning event evaluation "
                "identity does not match"
            )

        if (
            not raw_outcome_id
            or str(raw_outcome_id)
            != str(outcome.id)
        ):
            raise ValueError(
                "Business learning event outcome "
                "identity does not match"
            )


__all__ = [
    "CustomerSupportBusinessLearningMapper",
]
