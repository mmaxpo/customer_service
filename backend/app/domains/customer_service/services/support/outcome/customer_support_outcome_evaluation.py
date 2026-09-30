from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domains.customer_service.models.outcomes import (
    CustomerSupportOutcomeRecord,
)


class CustomerSupportOutcomeEvaluationResult(StrEnum):
    ACHIEVED = "achieved"
    PARTIALLY_ACHIEVED = "partially_achieved"
    PROGRESSING = "progressing"
    FAILED = "failed"
    INTENTIONALLY_NOT_EXECUTED = (
        "intentionally_not_executed"
    )
    INCONCLUSIVE = "inconclusive"


class CustomerSupportOutcomeEvaluation(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    evaluation_version: int = Field(
        default=1,
        ge=1,
    )

    result: CustomerSupportOutcomeEvaluationResult
    reason_code: str
    summary: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )
    retryable: bool = False

    achieved_operation_count: int = Field(
        ge=0
    )
    failed_operation_count: int = Field(
        ge=0
    )
    pending_operation_count: int = Field(
        ge=0
    )
    unknown_operation_count: int = Field(
        ge=0
    )
    not_executed_operation_count: int = Field(
        ge=0
    )

    observed_outcome: dict[str, Any] = Field(
        default_factory=dict
    )
    evidence: list[dict[str, Any]] = Field(
        default_factory=list
    )


class CustomerSupportOutcomeEvaluator:
    EVALUATION_VERSION = 1

    def evaluate(
        self,
        outcome: CustomerSupportOutcomeRecord,
    ) -> CustomerSupportOutcomeEvaluation:
        operations = [
            item
            for item in (
                outcome.operations_json or []
            )
            if isinstance(item, dict)
        ]

        counters = self._count_operations(
            operations
        )

        observed = {
            "decision": outcome.decision,
            "status": outcome.status,
            "operation_count": (
                outcome.operation_count
            ),
            **counters,
        }

        evidence = [
            {
                "kind": "canonical_support_outcome",
                "source": (
                    "customer_service."
                    "support_outcome"
                ),
                "data": {
                    "support_outcome_id": (
                        str(outcome.id)
                    ),
                    "review_plan_id": (
                        outcome.review_plan_id
                    ),
                    "outcome_version": (
                        outcome.outcome_version
                    ),
                },
            }
        ]

        if outcome.decision == "rejected":
            return self._result(
                result=(
                    CustomerSupportOutcomeEvaluationResult
                    .INTENTIONALLY_NOT_EXECUTED
                ),
                reason_code=(
                    "support_plan_rejected_by_human"
                ),
                summary=(
                    "The support plan was intentionally "
                    "not executed because it was rejected."
                ),
                confidence=1.0,
                counters=counters,
                observed=observed,
                evidence=evidence,
            )

        if not operations:
            return self._result(
                result=(
                    CustomerSupportOutcomeEvaluationResult
                    .INCONCLUSIVE
                ),
                reason_code=(
                    "approved_outcome_has_no_operations"
                ),
                summary=(
                    "The approved support outcome contains "
                    "no executable operation evidence."
                ),
                confidence=0.25,
                retryable=False,
                counters=counters,
                observed=observed,
                evidence=evidence,
            )

        if counters["failed_operation_count"] > 0:
            return self._result(
                result=(
                    CustomerSupportOutcomeEvaluationResult
                    .FAILED
                ),
                reason_code=(
                    "one_or_more_operations_failed"
                ),
                summary=(
                    "At least one required support "
                    "operation failed."
                ),
                confidence=1.0,
                counters=counters,
                observed=observed,
                evidence=evidence,
            )

        if (
            counters["achieved_operation_count"]
            == len(operations)
        ):
            return self._result(
                result=(
                    CustomerSupportOutcomeEvaluationResult
                    .ACHIEVED
                ),
                reason_code=(
                    "all_operations_completed"
                ),
                summary=(
                    "All required support operations "
                    "were completed."
                ),
                confidence=1.0,
                counters=counters,
                observed=observed,
                evidence=evidence,
            )

        if (
            counters["achieved_operation_count"] > 0
            and (
                counters["pending_operation_count"] > 0
                or counters[
                    "unknown_operation_count"
                ] > 0
            )
        ):
            return self._result(
                result=(
                    CustomerSupportOutcomeEvaluationResult
                    .PARTIALLY_ACHIEVED
                ),
                reason_code=(
                    "completed_and_incomplete_operations"
                ),
                summary=(
                    "Some support operations completed, "
                    "while others remain incomplete."
                ),
                confidence=0.9,
                counters=counters,
                observed=observed,
                evidence=evidence,
            )

        if (
            counters["pending_operation_count"] > 0
            and counters[
                "unknown_operation_count"
            ] == 0
        ):
            return self._result(
                result=(
                    CustomerSupportOutcomeEvaluationResult
                    .PROGRESSING
                ),
                reason_code=(
                    "operations_prepared_or_submitted"
                ),
                summary=(
                    "The required support operations "
                    "were prepared or submitted but are "
                    "not yet fully completed."
                ),
                confidence=0.9,
                counters=counters,
                observed=observed,
                evidence=evidence,
            )

        return self._result(
            result=(
                CustomerSupportOutcomeEvaluationResult
                .INCONCLUSIVE
            ),
            reason_code=(
                "insufficient_operation_evidence"
            ),
            summary=(
                "The support outcome does not contain "
                "enough normalized evidence to establish "
                "achievement."
            ),
            confidence=0.35,
            retryable=False,
            counters=counters,
            observed=observed,
            evidence=evidence,
        )

    @staticmethod
    def _count_operations(
        operations: list[dict[str, Any]],
    ) -> dict[str, int]:
        achieved = 0
        failed = 0
        pending = 0
        unknown = 0
        not_executed = 0

        for operation in operations:
            status = str(
                operation.get("status") or ""
            ).strip().lower()

            if status == "completed":
                achieved += 1
            elif status == "failed":
                failed += 1
            elif status in {
                "prepared",
                "submitted",
            }:
                pending += 1
            elif status == "rejected":
                not_executed += 1
            else:
                unknown += 1

        return {
            "achieved_operation_count": achieved,
            "failed_operation_count": failed,
            "pending_operation_count": pending,
            "unknown_operation_count": unknown,
            "not_executed_operation_count": (
                not_executed
            ),
        }

    def _result(
        self,
        *,
        result: (
            CustomerSupportOutcomeEvaluationResult
        ),
        reason_code: str,
        summary: str,
        confidence: float,
        counters: dict[str, int],
        observed: dict[str, Any],
        evidence: list[dict[str, Any]],
        retryable: bool = False,
    ) -> CustomerSupportOutcomeEvaluation:
        return CustomerSupportOutcomeEvaluation(
            evaluation_version=(
                self.EVALUATION_VERSION
            ),
            result=result,
            reason_code=reason_code,
            summary=summary,
            confidence=confidence,
            retryable=retryable,
            observed_outcome=observed,
            evidence=evidence,
            **counters,
        )


__all__ = [
    "CustomerSupportOutcomeEvaluation",
    "CustomerSupportOutcomeEvaluationResult",
    "CustomerSupportOutcomeEvaluator",
]
