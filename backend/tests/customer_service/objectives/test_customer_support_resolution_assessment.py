from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domains.customer_service.services.support.resolution.customer_support_resolution_assessment import (
    CustomerSupportResolutionAssessmentAdapter,
)
from app.runtime.objectives.resolution import (
    ObjectiveOperationStatus,
    ObjectiveResolutionContext,
    ObjectiveResolutionStatus,
)


def _outcome(
    *,
    statuses: list[str],
    operation_refs: list[str | None] | None = None,
    decision: str = "approved",
):
    outcome_id = uuid4()
    user_id = uuid4()
    review_plan_id = "review-1"

    refs = (
        operation_refs
        if operation_refs is not None
        else [
            f"support-operation-{index}"
            for index in range(
                1,
                len(statuses) + 1,
            )
        ]
    )

    operations = []

    for index, status in enumerate(statuses):
        operation = {
            "operation_type": (
                "whole_refund"
                if index == 0
                else "replacement"
            ),
            "status": status,
            "item_id": (
                None
                if index == 0
                else f"item-{index}"
            ),
            "provider_result": {
                "secret": "must-not-leak",
            },
        }

        if refs[index] is not None:
            operation["operation_ref"] = refs[index]

        operations.append(operation)

    return SimpleNamespace(
        id=outcome_id,
        user_id=user_id,
        review_plan_id=review_plan_id,
        workflow_run_id=uuid4(),
        objective_namespace=(
            "customer_service.support"
        ),
        objective_ref=review_plan_id,
        objective_type=(
            "whole_refund"
            if len(statuses) == 1
            else "multi_operation"
        ),
        source_objective_version=1,
        outcome_version=1,
        decision=decision,
        status=(
            statuses[0]
            if len(set(statuses)) == 1
            else "mixed"
        ),
        operations_json=operations,
    )


def _evaluation(
    outcome,
    *,
    result: str,
    achieved: int = 0,
    failed: int = 0,
    pending: int = 0,
    unknown: int = 0,
    not_executed: int = 0,
):
    return SimpleNamespace(
        id=uuid4(),
        user_id=outcome.user_id,
        support_outcome_id=outcome.id,
        review_plan_id=outcome.review_plan_id,
        evaluation_version=1,
        result=result,
        reason_code=f"{result}_reason",
        summary=f"Objective is {result}.",
        confidence=0.9,
        achieved_operation_count=achieved,
        failed_operation_count=failed,
        pending_operation_count=pending,
        unknown_operation_count=unknown,
        not_executed_operation_count=(
            not_executed
        ),
        evidence_json=[
            {
                "kind": "canonical_outcome",
                "source": "customer_service",
                "data": {
                    "private": "not-projected",
                },
            }
        ],
    )


def _assess(outcome, evaluation):
    return (
        CustomerSupportResolutionAssessmentAdapter()
        .assess(
            ObjectiveResolutionContext(
                outcome=outcome,
                evaluation=evaluation,
            )
        )
    )


def test_all_operations_completed_is_terminal_achieved():
    outcome = _outcome(
        statuses=["completed"],
    )
    evaluation = _evaluation(
        outcome,
        result="achieved",
        achieved=1,
    )

    assessment = _assess(
        outcome,
        evaluation,
    )

    assert (
        assessment.status
        == ObjectiveResolutionStatus.ACHIEVED
    )
    assert assessment.is_terminal is True
    assert assessment.unresolved_operation_refs == ()
    assert assessment.achieved_operation_refs == (
        "support-operation-1",
    )


def test_completed_and_submitted_is_partial():
    outcome = _outcome(
        statuses=[
            "completed",
            "submitted",
        ],
    )
    evaluation = _evaluation(
        outcome,
        result="partially_achieved",
        achieved=1,
        pending=1,
    )

    assessment = _assess(
        outcome,
        evaluation,
    )

    assert assessment.status == (
        ObjectiveResolutionStatus
        .PARTIALLY_ACHIEVED
    )
    assert assessment.is_terminal is False
    assert assessment.unresolved_operation_refs == (
        "support-operation-2",
    )


def test_submitted_operation_is_progressing():
    outcome = _outcome(
        statuses=["submitted"],
    )
    evaluation = _evaluation(
        outcome,
        result="progressing",
        pending=1,
    )

    assessment = _assess(
        outcome,
        evaluation,
    )

    assert assessment.status == (
        ObjectiveResolutionStatus.PROGRESSING
    )
    assert assessment.operations[0].status == (
        ObjectiveOperationStatus.PENDING
    )


def test_failed_operation_remains_unresolved():
    outcome = _outcome(
        statuses=["failed"],
    )
    evaluation = _evaluation(
        outcome,
        result="failed",
        failed=1,
    )

    assessment = _assess(
        outcome,
        evaluation,
    )

    assert assessment.status == (
        ObjectiveResolutionStatus.FAILED
    )
    assert assessment.is_terminal is False
    assert assessment.failed_operation_refs == (
        "support-operation-1",
    )
    assert assessment.unresolved_operation_refs == (
        "support-operation-1",
    )


def test_unknown_operation_is_inconclusive():
    outcome = _outcome(
        statuses=["unknown"],
    )
    evaluation = _evaluation(
        outcome,
        result="inconclusive",
        unknown=1,
    )

    assessment = _assess(
        outcome,
        evaluation,
    )

    assert assessment.status == (
        ObjectiveResolutionStatus.INCONCLUSIVE
    )
    assert assessment.unknown_operation_refs == (
        "support-operation-1",
    )


def test_human_rejection_is_terminal_nonexecution():
    outcome = _outcome(
        statuses=["rejected"],
        decision="rejected",
    )
    evaluation = _evaluation(
        outcome,
        result="intentionally_not_executed",
        not_executed=1,
    )

    assessment = _assess(
        outcome,
        evaluation,
    )

    assert assessment.status == (
        ObjectiveResolutionStatus
        .INTENTIONALLY_NOT_EXECUTED
    )
    assert assessment.is_terminal is True
    assert (
        assessment.not_executed_operation_refs
        == ("support-operation-1",)
    )
    assert assessment.unresolved_operation_refs == ()


def test_legacy_operation_refs_are_deterministic():
    outcome = _outcome(
        statuses=["failed", "failed"],
        operation_refs=[None, None],
    )
    evaluation = _evaluation(
        outcome,
        result="failed",
        failed=2,
    )

    first = _assess(
        outcome,
        evaluation,
    )
    second = _assess(
        outcome,
        evaluation,
    )

    first_refs = tuple(
        item.operation_ref
        for item in first.operations
    )
    second_refs = tuple(
        item.operation_ref
        for item in second.operations
    )

    assert first_refs == second_refs
    assert len(set(first_refs)) == 2
    assert all(
        value.startswith(
            "support_operation:legacy:"
        )
        for value in first_refs
    )


def test_multiple_same_type_operations_remain_distinct():
    outcome = _outcome(
        statuses=["failed", "failed"],
        operation_refs=[
            "refund-item-1",
            "refund-item-2",
        ],
    )

    outcome.operations_json[1][
        "operation_type"
    ] = "whole_refund"

    evaluation = _evaluation(
        outcome,
        result="failed",
        failed=2,
    )

    assessment = _assess(
        outcome,
        evaluation,
    )

    assert assessment.failed_operation_refs == (
        "refund-item-1",
        "refund-item-2",
    )


def test_provider_payload_does_not_leak():
    outcome = _outcome(
        statuses=["failed"],
    )
    evaluation = _evaluation(
        outcome,
        result="failed",
        failed=1,
    )

    assessment = _assess(
        outcome,
        evaluation,
    )

    serialized = assessment.model_dump_json()

    assert "must-not-leak" not in serialized
    assert "not-projected" not in serialized


def test_outcome_evaluation_lineage_mismatch_rejected():
    outcome = _outcome(
        statuses=["completed"],
    )
    evaluation = _evaluation(
        outcome,
        result="achieved",
        achieved=1,
    )
    evaluation.support_outcome_id = uuid4()

    with pytest.raises(
        ValueError,
        match="does not belong to outcome",
    ):
        _assess(
            outcome,
            evaluation,
        )


def test_counter_mismatch_rejected():
    outcome = _outcome(
        statuses=["failed"],
    )
    evaluation = _evaluation(
        outcome,
        result="failed",
        failed=0,
    )

    with pytest.raises(
        ValueError,
        match=(
            "failed_operation_count does not match"
        ),
    ):
        _assess(
            outcome,
            evaluation,
        )
