from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.runtime.objectives.resolution import (
    ObjectiveOperationResolution,
    ObjectiveOperationStatus,
    ObjectiveReference,
    ObjectiveResolutionAssessment,
    ObjectiveResolutionSource,
    ObjectiveResolutionStatus,
)


def _assessment(
    *,
    status=ObjectiveResolutionStatus
    .PARTIALLY_ACHIEVED,
    terminal=False,
    operations=(),
):
    return ObjectiveResolutionAssessment(
        objective=ObjectiveReference(
            namespace="customer_service.support",
            objective_type="multi_operation",
            objective_ref="review-1",
            objective_version=1,
        ),
        source=ObjectiveResolutionSource(
            outcome_ref="outcome-1",
            outcome_version=1,
            evaluation_ref="evaluation-1",
            evaluation_version=1,
            workflow_run_id="run-1",
        ),
        status=status,
        reason_code="test_result",
        summary="Test assessment.",
        confidence=0.9,
        is_terminal=terminal,
        operations=operations,
    )


def test_assessment_derives_operation_groups():
    assessment = _assessment(
        operations=(
            ObjectiveOperationResolution(
                operation_ref="operation-1",
                operation_type="refund",
                status=(
                    ObjectiveOperationStatus.ACHIEVED
                ),
            ),
            ObjectiveOperationResolution(
                operation_ref="operation-2",
                operation_type="replacement",
                status=(
                    ObjectiveOperationStatus.PENDING
                ),
            ),
            ObjectiveOperationResolution(
                operation_ref="operation-3",
                operation_type="notification",
                status=(
                    ObjectiveOperationStatus.FAILED
                ),
            ),
        )
    )

    assert assessment.achieved_operation_refs == (
        "operation-1",
    )
    assert assessment.pending_operation_refs == (
        "operation-2",
    )
    assert assessment.failed_operation_refs == (
        "operation-3",
    )
    assert assessment.unresolved_operation_refs == (
        "operation-2",
        "operation-3",
    )


def test_same_operation_ref_is_valid_for_different_objectives():
    first = _assessment(
        operations=(
            ObjectiveOperationResolution(
                operation_ref="operation-1",
                operation_type="refund",
                status=(
                    ObjectiveOperationStatus.ACHIEVED
                ),
            ),
        )
    )

    second = ObjectiveResolutionAssessment(
        objective=ObjectiveReference(
            namespace="customer_service.support",
            objective_type="whole_refund",
            objective_ref="review-2",
            objective_version=1,
        ),
        source=ObjectiveResolutionSource(
            outcome_ref="outcome-2",
            outcome_version=1,
            evaluation_ref="evaluation-2",
            evaluation_version=1,
        ),
        status=ObjectiveResolutionStatus.ACHIEVED,
        reason_code="all_operations_completed",
        summary="Completed.",
        confidence=1.0,
        is_terminal=True,
        operations=(
            ObjectiveOperationResolution(
                operation_ref="operation-1",
                operation_type="refund",
                status=(
                    ObjectiveOperationStatus.ACHIEVED
                ),
            ),
        ),
    )

    assert (
        first.objective.objective_ref
        != second.objective.objective_ref
    )
    assert (
        first.operations[0].operation_ref
        == second.operations[0].operation_ref
    )


def test_duplicate_operation_refs_are_rejected():
    with pytest.raises(
        ValidationError,
        match="operation refs must be unique",
    ):
        _assessment(
            operations=(
                ObjectiveOperationResolution(
                    operation_ref="operation-1",
                    operation_type="refund",
                    status=(
                        ObjectiveOperationStatus
                        .ACHIEVED
                    ),
                ),
                ObjectiveOperationResolution(
                    operation_ref="operation-1",
                    operation_type="replacement",
                    status=(
                        ObjectiveOperationStatus
                        .FAILED
                    ),
                ),
            )
        )


def test_inconsistent_group_is_rejected():
    with pytest.raises(
        ValidationError,
        match=(
            "failed_operation_refs does not match"
        ),
    ):
        ObjectiveResolutionAssessment(
            objective=ObjectiveReference(
                namespace="support",
                objective_type="refund",
                objective_ref="objective-1",
                objective_version=1,
            ),
            source=ObjectiveResolutionSource(
                outcome_ref="outcome-1",
                outcome_version=1,
                evaluation_ref="evaluation-1",
                evaluation_version=1,
            ),
            status=ObjectiveResolutionStatus.FAILED,
            reason_code="failed",
            summary="Failed.",
            confidence=1.0,
            is_terminal=False,
            operations=(
                ObjectiveOperationResolution(
                    operation_ref="operation-1",
                    operation_type="refund",
                    status=(
                        ObjectiveOperationStatus
                        .FAILED
                    ),
                ),
            ),
            failed_operation_refs=("wrong-ref",),
        )


def test_achieved_assessment_must_be_terminal():
    with pytest.raises(
        ValidationError,
        match="achieved objective must be terminal",
    ):
        _assessment(
            status=ObjectiveResolutionStatus.ACHIEVED,
            terminal=False,
        )


def test_achieved_assessment_cannot_have_unresolved_work():
    with pytest.raises(
        ValidationError,
        match=(
            "achieved objective cannot contain "
            "unresolved operations"
        ),
    ):
        _assessment(
            status=ObjectiveResolutionStatus.ACHIEVED,
            terminal=True,
            operations=(
                ObjectiveOperationResolution(
                    operation_ref="operation-1",
                    operation_type="refund",
                    status=(
                        ObjectiveOperationStatus
                        .PENDING
                    ),
                ),
            ),
        )


def test_progressing_assessment_cannot_be_terminal():
    with pytest.raises(
        ValidationError,
        match=(
            "progressing objective cannot be terminal"
        ),
    ):
        _assessment(
            status=(
                ObjectiveResolutionStatus.PROGRESSING
            ),
            terminal=True,
        )


def test_contract_round_trip_is_lossless():
    original = _assessment(
        operations=(
            ObjectiveOperationResolution(
                operation_ref="operation-1",
                operation_type="refund",
                status=(
                    ObjectiveOperationStatus.ACHIEVED
                ),
                evidence_refs=("evidence-1",),
            ),
        )
    )

    restored = (
        ObjectiveResolutionAssessment
        .model_validate(
            original.model_dump(
                mode="json",
            )
        )
    )

    assert restored == original


def test_core_contract_does_not_import_customer_service():
    module_name = (
        "app.runtime.objectives."
        "resolution.contracts"
    )

    module = __import__(
        module_name,
        fromlist=["*"],
    )

    source_file = module.__file__

    assert source_file is not None

    with open(
        source_file,
        encoding="utf-8",
    ) as handle:
        source = handle.read()

    assert (
        "app.domains.customer_service"
        not in source
    )
