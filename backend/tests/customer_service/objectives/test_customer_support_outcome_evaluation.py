from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domains.customer_service.services.support.outcome.customer_support_outcome_evaluation import (
    CustomerSupportOutcomeEvaluationResult,
    CustomerSupportOutcomeEvaluator,
)


def _outcome(
    *,
    decision: str = "approved",
    statuses: list[str],
):
    return SimpleNamespace(
        id=uuid4(),
        review_plan_id=str(uuid4()),
        outcome_version=1,
        decision=decision,
        status=(
            statuses[0]
            if statuses
            and len(set(statuses)) == 1
            else "mixed"
        ),
        operation_count=len(statuses),
        operations_json=[
            {
                "operation_type": (
                    "whole_refund"
                ),
                "status": status,
            }
            for status in statuses
        ],
    )


@pytest.mark.parametrize(
    (
        "statuses",
        "expected_result",
        "expected_reason",
    ),
    [
        (
            ["completed"],
            CustomerSupportOutcomeEvaluationResult
            .ACHIEVED,
            "all_operations_completed",
        ),
        (
            ["prepared"],
            CustomerSupportOutcomeEvaluationResult
            .PROGRESSING,
            "operations_prepared_or_submitted",
        ),
        (
            ["submitted"],
            CustomerSupportOutcomeEvaluationResult
            .PROGRESSING,
            "operations_prepared_or_submitted",
        ),
        (
            ["completed", "prepared"],
            CustomerSupportOutcomeEvaluationResult
            .PARTIALLY_ACHIEVED,
            "completed_and_incomplete_operations",
        ),
        (
            ["failed"],
            CustomerSupportOutcomeEvaluationResult
            .FAILED,
            "one_or_more_operations_failed",
        ),
        (
            ["completed", "failed"],
            CustomerSupportOutcomeEvaluationResult
            .FAILED,
            "one_or_more_operations_failed",
        ),
        (
            ["unknown"],
            CustomerSupportOutcomeEvaluationResult
            .INCONCLUSIVE,
            "insufficient_operation_evidence",
        ),
    ],
)
def test_deterministic_classification(
    statuses,
    expected_result,
    expected_reason,
):
    result = (
        CustomerSupportOutcomeEvaluator()
        .evaluate(
            _outcome(statuses=statuses)
        )
    )

    assert result.result == expected_result
    assert result.reason_code == expected_reason


def test_rejected_plan_is_intentionally_not_executed():
    result = (
        CustomerSupportOutcomeEvaluator()
        .evaluate(
            _outcome(
                decision="rejected",
                statuses=[
                    "rejected",
                    "rejected",
                ],
            )
        )
    )

    assert (
        result.result
        == CustomerSupportOutcomeEvaluationResult
        .INTENTIONALLY_NOT_EXECUTED
    )
    assert (
        result.reason_code
        == "support_plan_rejected_by_human"
    )
    assert (
        result.not_executed_operation_count
        == 2
    )
    assert result.unknown_operation_count == 0
    assert result.failed_operation_count == 0
    assert result.confidence == 1.0


def test_approved_outcome_without_operations_is_inconclusive():
    result = (
        CustomerSupportOutcomeEvaluator()
        .evaluate(
            _outcome(statuses=[])
        )
    )

    assert (
        result.result
        == CustomerSupportOutcomeEvaluationResult
        .INCONCLUSIVE
    )
    assert (
        result.reason_code
        == "approved_outcome_has_no_operations"
    )
    assert result.confidence == 0.25


def test_operation_counters_are_preserved():
    result = (
        CustomerSupportOutcomeEvaluator()
        .evaluate(
            _outcome(
                statuses=[
                    "completed",
                    "failed",
                    "prepared",
                    "submitted",
                    "rejected",
                    "unknown",
                ]
            )
        )
    )

    assert result.achieved_operation_count == 1
    assert result.failed_operation_count == 1
    assert result.pending_operation_count == 2
    assert (
        result.not_executed_operation_count
        == 1
    )
    assert result.unknown_operation_count == 1

    assert (
        result.result
        == CustomerSupportOutcomeEvaluationResult
        .FAILED
    )
