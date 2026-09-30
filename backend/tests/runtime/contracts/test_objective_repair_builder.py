import pytest

from app.runtime.objectives.repair import (
    ObjectiveRepairConstraints,
    ObjectiveRepairDisposition,
    ObjectiveRepairRequestBuilder,
    build_objective_repair_request_ref,
)
from app.runtime.objectives.resolution import (
    ObjectiveOperationResolution,
    ObjectiveOperationStatus,
    ObjectiveReference,
    ObjectiveResolutionAssessment,
    ObjectiveResolutionSource,
    ObjectiveResolutionStatus,
)


def _terminal_assessment(
    *,
    status,
):
    operation_status = (
        ObjectiveOperationStatus.ACHIEVED
        if status
        == ObjectiveResolutionStatus.ACHIEVED
        else ObjectiveOperationStatus.NOT_EXECUTED
    )

    return ObjectiveResolutionAssessment(
        objective=ObjectiveReference(
            namespace="example.support",
            objective_type="refund_and_replace",
            objective_ref="objective-1",
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
        reason_code="terminal_resolution",
        summary="The objective is terminal.",
        confidence=1.0,
        is_terminal=True,
        operations=(
            ObjectiveOperationResolution(
                operation_ref="operation-1",
                operation_type="refund",
                status=operation_status,
                required=True,
            ),
        ),
    )


def _constraints(
    *,
    maximum_target_count=None,
):
    return ObjectiveRepairConstraints(
        allowed_dispositions=(
            ObjectiveRepairDisposition
            .RETRY_OPERATION,
            ObjectiveRepairDisposition
            .WAIT_FOR_RESULT,
            ObjectiveRepairDisposition
            .REPLAN_REMAINING,
            ObjectiveRepairDisposition
            .REQUEST_HUMAN_ACTION,
            ObjectiveRepairDisposition
            .STOP_REPAIR,
        ),
        maximum_target_count=(
            maximum_target_count
        ),
    )


def _assessment(
    *,
    status=(
        ObjectiveResolutionStatus
        .PARTIALLY_ACHIEVED
    ),
    terminal=False,
):
    return ObjectiveResolutionAssessment(
        objective=ObjectiveReference(
            namespace="example.support",
            objective_type="refund_and_replace",
            objective_ref="objective-1",
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
        reason_code=(
            "completed_and_incomplete_operations"
        ),
        summary="One operation remains unresolved.",
        confidence=0.9,
        is_terminal=terminal,
        operations=(
            ObjectiveOperationResolution(
                operation_ref="operation-1",
                operation_type="refund",
                status=(
                    ObjectiveOperationStatus
                    .ACHIEVED
                ),
                required=True,
            ),
            ObjectiveOperationResolution(
                operation_ref="operation-2",
                operation_type="replacement",
                status=(
                    ObjectiveOperationStatus
                    .FAILED
                ),
                required=True,
                reason_code="provider_failure",
                summary="Replacement failed.",
                source_task_id="task-2",
                verification_ref=(
                    "verification-2"
                ),
                evidence_refs=("evidence-2",),
                metadata={
                    "safe_context": "retained",
                },
            ),
            ObjectiveOperationResolution(
                operation_ref="operation-3",
                operation_type="notification",
                status=(
                    ObjectiveOperationStatus
                    .UNKNOWN
                ),
                required=False,
            ),
        ),
    )


def test_request_ref_is_deterministic():
    first = build_objective_repair_request_ref(
        resolution_record_ref="resolution-1"
    )
    second = build_objective_repair_request_ref(
        resolution_record_ref="resolution-1"
    )

    assert first == second
    assert first == (
        "objective-repair:resolution-1:v1"
    )


def test_request_ref_changes_by_version():
    assert (
        build_objective_repair_request_ref(
            resolution_record_ref="resolution-1",
            request_version=2,
        )
        == "objective-repair:resolution-1:v2"
    )


def test_builder_selects_only_required_unresolved():
    request = ObjectiveRepairRequestBuilder().build(
        resolution_record_ref="resolution-1",
        resolution_projection_version=1,
        assessment=_assessment(),
        constraints=_constraints(),
        context={
            "safe": True,
        },
    )

    assert request.repair_request_ref == (
        "objective-repair:resolution-1:v1"
    )
    assert tuple(
        target.operation_ref
        for target in request.targets
    ) == ("operation-2",)

    target = request.targets[0]

    assert target.resolution_status == (
        ObjectiveOperationStatus.FAILED
    )
    assert target.source_task_id == "task-2"
    assert target.verification_ref == (
        "verification-2"
    )
    assert target.evidence_refs == (
        "evidence-2",
    )
    assert target.metadata == {
        "safe_context": "retained",
    }


def test_builder_preserves_resolution_lineage():
    request = ObjectiveRepairRequestBuilder().build(
        resolution_record_ref="resolution-1",
        resolution_projection_version=3,
        assessment=_assessment(),
        constraints=_constraints(),
    )

    assert request.source.objective.objective_ref == (
        "objective-1"
    )
    assert request.source.outcome_ref == "outcome-1"
    assert request.source.evaluation_ref == (
        "evaluation-1"
    )
    assert (
        request.source
        .resolution_projection_version
        == 3
    )
    assert request.source.workflow_run_id == "run-1"


@pytest.mark.parametrize(
    "status",
    [
        ObjectiveResolutionStatus.ACHIEVED,
        (
            ObjectiveResolutionStatus
            .INTENTIONALLY_NOT_EXECUTED
        ),
    ],
)
def test_builder_rejects_terminal_resolution(
    status,
):
    with pytest.raises(
        ValueError,
        match="terminal objective",
    ):
        ObjectiveRepairRequestBuilder().build(
            resolution_record_ref="resolution-1",
            resolution_projection_version=1,
            assessment=_terminal_assessment(
                status=status,
            ),
            constraints=_constraints(),
        )


def test_builder_rejects_nonterminal_without_targets():
    assessment = ObjectiveResolutionAssessment(
        objective=ObjectiveReference(
            namespace="example.support",
            objective_type="status_check",
            objective_ref="objective-1",
            objective_version=1,
        ),
        source=ObjectiveResolutionSource(
            outcome_ref="outcome-1",
            outcome_version=1,
            evaluation_ref="evaluation-1",
            evaluation_version=1,
        ),
        status=(
            ObjectiveResolutionStatus
            .INCONCLUSIVE
        ),
        reason_code="insufficient_evidence",
        summary="No required operation is unresolved.",
        confidence=0.4,
        is_terminal=False,
        operations=(
            ObjectiveOperationResolution(
                operation_ref="operation-1",
                operation_type="status_check",
                status=(
                    ObjectiveOperationStatus
                    .UNKNOWN
                ),
                required=False,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="no repairable unresolved",
    ):
        ObjectiveRepairRequestBuilder().build(
            resolution_record_ref="resolution-1",
            resolution_projection_version=1,
            assessment=assessment,
            constraints=_constraints(),
        )


def test_builder_enforces_maximum_target_count():
    assessment = _assessment().model_copy(
        update={
            "operations": (
                *_assessment().operations,
                ObjectiveOperationResolution(
                    operation_ref="operation-4",
                    operation_type="reship",
                    status=(
                        ObjectiveOperationStatus
                        .PENDING
                    ),
                    required=True,
                ),
            ),
            "unresolved_operation_refs": (
                "operation-2",
                "operation-4",
            ),
            "pending_operation_refs": (
                "operation-4",
            ),
        }
    )

    assessment = (
        ObjectiveResolutionAssessment
        .model_validate(
            assessment.model_dump(
                mode="json"
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="exceeds maximum target count",
    ):
        ObjectiveRepairRequestBuilder().build(
            resolution_record_ref="resolution-1",
            resolution_projection_version=1,
            assessment=assessment,
            constraints=_constraints(
                maximum_target_count=1,
            ),
        )
