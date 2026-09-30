from datetime import (
    datetime,
    timezone,
)

import pytest
from pydantic import ValidationError

from app.runtime.objectives.repair import (
    ObjectiveRepairAction,
    ObjectiveRepairConstraints,
    ObjectiveRepairDisposition,
    ObjectiveRepairPlan,
    ObjectiveRepairRequest,
    ObjectiveRepairSource,
    ObjectiveRepairTarget,
)
from app.runtime.objectives.resolution import (
    ObjectiveOperationStatus,
    ObjectiveReference,
    ObjectiveResolutionStatus,
)


def _objective():
    return ObjectiveReference(
        namespace="example.support",
        objective_type="refund_and_replace",
        objective_ref="objective-1",
        objective_version=1,
    )


def _source():
    return ObjectiveRepairSource(
        resolution_record_ref="resolution-1",
        objective=_objective(),
        outcome_ref="outcome-1",
        outcome_version=1,
        evaluation_ref="evaluation-1",
        evaluation_version=1,
        resolution_projection_version=1,
        workflow_run_id="run-1",
    )


def _constraints(
    *,
    automatic=False,
    approval=False,
):
    return ObjectiveRepairConstraints(
        allow_automatic_execution=automatic,
        require_human_approval=approval,
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
    )


def _target(
    *,
    operation_ref="operation-1",
    status=ObjectiveOperationStatus.FAILED,
):
    return ObjectiveRepairTarget(
        operation_ref=operation_ref,
        operation_type="refund",
        resolution_status=status,
        required=True,
    )


def _request():
    return ObjectiveRepairRequest(
        repair_request_ref=(
            "objective-repair:resolution-1:v1"
        ),
        source=_source(),
        resolution_status=(
            ObjectiveResolutionStatus.FAILED
        ),
        resolution_reason_code=(
            "operation_failed"
        ),
        resolution_summary=(
            "One operation failed."
        ),
        resolution_confidence=0.9,
        targets=(_target(),),
        constraints=_constraints(),
    )


def _retry_action(
    *,
    operation_ref="operation-1",
):
    return ObjectiveRepairAction(
        action_ref="action-1",
        disposition=(
            ObjectiveRepairDisposition
            .RETRY_OPERATION
        ),
        target_operation_refs=(
            operation_ref,
        ),
        reason_code="retryable_failure",
        summary="Retry the failed operation.",
        confidence=0.9,
    )


def test_valid_repair_request():
    request = _request()

    assert request.source.objective == _objective()
    assert request.targets[0].operation_ref == (
        "operation-1"
    )


@pytest.mark.parametrize(
    "status",
    [
        ObjectiveOperationStatus.ACHIEVED,
        ObjectiveOperationStatus.NOT_EXECUTED,
    ],
)
def test_repair_target_rejects_resolved_status(
    status,
):
    with pytest.raises(
        ValidationError,
        match="failed, pending, or unknown",
    ):
        _target(status=status)


def test_repair_target_must_be_required():
    with pytest.raises(
        ValidationError,
        match="required operation",
    ):
        ObjectiveRepairTarget(
            operation_ref="operation-1",
            operation_type="refund",
            resolution_status=(
                ObjectiveOperationStatus.FAILED
            ),
            required=False,
        )


def test_constraints_require_allowed_disposition():
    with pytest.raises(
        ValidationError,
        match="at least one",
    ):
        ObjectiveRepairConstraints(
            allowed_dispositions=(),
        )


def test_constraints_reject_duplicate_dispositions():
    with pytest.raises(
        ValidationError,
        match="must be unique",
    ):
        ObjectiveRepairConstraints(
            allowed_dispositions=(
                ObjectiveRepairDisposition
                .RETRY_OPERATION,
                ObjectiveRepairDisposition
                .RETRY_OPERATION,
            ),
        )


def test_constraints_reject_automatic_and_approval():
    with pytest.raises(
        ValidationError,
        match="cannot both",
    ):
        _constraints(
            automatic=True,
            approval=True,
        )


def test_constraints_require_timezone_aware_not_before():
    with pytest.raises(
        ValidationError,
        match="timezone-aware",
    ):
        ObjectiveRepairConstraints(
            allowed_dispositions=(
                ObjectiveRepairDisposition
                .WAIT_FOR_RESULT,
            ),
            not_before=datetime(2026, 8, 3),
        )


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
def test_request_rejects_terminal_resolved_status(
    status,
):
    with pytest.raises(
        ValidationError,
        match="cannot produce a repair request",
    ):
        ObjectiveRepairRequest(
            repair_request_ref="request-1",
            source=_source(),
            resolution_status=status,
            resolution_reason_code="resolved",
            resolution_summary="Resolved.",
            resolution_confidence=1.0,
            targets=(_target(),),
            constraints=_constraints(),
        )


def test_request_rejects_duplicate_targets():
    with pytest.raises(
        ValidationError,
        match="must be unique",
    ):
        ObjectiveRepairRequest(
            repair_request_ref="request-1",
            source=_source(),
            resolution_status=(
                ObjectiveResolutionStatus.FAILED
            ),
            resolution_reason_code="failed",
            resolution_summary="Failed.",
            resolution_confidence=0.8,
            targets=(
                _target(),
                _target(),
            ),
            constraints=_constraints(),
        )


def test_wait_action_requires_wait_instruction():
    with pytest.raises(
        ValidationError,
        match="requires wait_until",
    ):
        ObjectiveRepairAction(
            action_ref="action-1",
            disposition=(
                ObjectiveRepairDisposition
                .WAIT_FOR_RESULT
            ),
            target_operation_refs=(
                "operation-1",
            ),
            reason_code="still_processing",
            summary="Wait.",
            confidence=0.8,
        )


def test_wait_action_accepts_event_instruction():
    action = ObjectiveRepairAction(
        action_ref="action-1",
        disposition=(
            ObjectiveRepairDisposition
            .WAIT_FOR_RESULT
        ),
        target_operation_refs=(
            "operation-1",
        ),
        reason_code="still_processing",
        summary="Wait for provider event.",
        confidence=0.8,
        wait_for_event_type=(
            "provider.operation.completed"
        ),
    )

    assert action.wait_for_event_type == (
        "provider.operation.completed"
    )


def test_non_wait_action_rejects_wait_instruction():
    with pytest.raises(
        ValidationError,
        match="cannot contain wait",
    ):
        ObjectiveRepairAction(
            action_ref="action-1",
            disposition=(
                ObjectiveRepairDisposition
                .RETRY_OPERATION
            ),
            target_operation_refs=(
                "operation-1",
            ),
            reason_code="failed",
            summary="Retry.",
            confidence=0.8,
            wait_until=datetime.now(timezone.utc),
        )


def test_human_action_requires_approval():
    with pytest.raises(
        ValidationError,
        match="must require human approval",
    ):
        ObjectiveRepairAction(
            action_ref="action-1",
            disposition=(
                ObjectiveRepairDisposition
                .REQUEST_HUMAN_ACTION
            ),
            target_operation_refs=(
                "operation-1",
            ),
            reason_code="manual_review",
            summary="Review manually.",
            confidence=0.8,
        )


def test_stop_action_rejects_automatic_execution():
    with pytest.raises(
        ValidationError,
        match="cannot allow automatic",
    ):
        ObjectiveRepairAction(
            action_ref="action-1",
            disposition=(
                ObjectiveRepairDisposition
                .STOP_REPAIR
            ),
            target_operation_refs=(
                "operation-1",
            ),
            reason_code="unsafe",
            summary="Stop.",
            confidence=0.8,
            automatic_execution_allowed=True,
        )


def test_valid_repair_plan():
    plan = ObjectiveRepairPlan(
        repair_request_ref=(
            _request().repair_request_ref
        ),
        objective=_objective(),
        disposition=(
            ObjectiveRepairDisposition
            .RETRY_OPERATION
        ),
        reason_code="retryable_failure",
        summary="Retry failed operation.",
        confidence=0.9,
        actions=(_retry_action(),),
        planned_target_refs=(
            "operation-1",
        ),
    )

    assert plan.planned_target_refs == (
        "operation-1",
    )


def test_plan_rejects_duplicate_target_across_actions():
    with pytest.raises(
        ValidationError,
        match="multiple actions",
    ):
        ObjectiveRepairPlan(
            repair_request_ref="request-1",
            objective=_objective(),
            disposition=(
                ObjectiveRepairDisposition
                .REPLAN_REMAINING
            ),
            reason_code="multiple",
            summary="Multiple actions.",
            confidence=0.8,
            actions=(
                _retry_action(),
                ObjectiveRepairAction(
                    action_ref="action-2",
                    disposition=(
                        ObjectiveRepairDisposition
                        .REPLAN_REMAINING
                    ),
                    target_operation_refs=(
                        "operation-1",
                    ),
                    reason_code="replan",
                    summary="Replan.",
                    confidence=0.8,
                ),
            ),
            planned_target_refs=(
                "operation-1",
            ),
        )


def test_plan_rejects_action_coverage_mismatch():
    with pytest.raises(
        ValidationError,
        match="exactly match",
    ):
        ObjectiveRepairPlan(
            repair_request_ref="request-1",
            objective=_objective(),
            disposition=(
                ObjectiveRepairDisposition
                .RETRY_OPERATION
            ),
            reason_code="retry",
            summary="Retry.",
            confidence=0.8,
            actions=(_retry_action(),),
            planned_target_refs=(
                "operation-2",
            ),
        )


def test_plan_rejects_overlapping_coverage_groups():
    with pytest.raises(
        ValidationError,
        match="must be disjoint",
    ):
        ObjectiveRepairPlan(
            repair_request_ref="request-1",
            objective=_objective(),
            disposition=(
                ObjectiveRepairDisposition
                .RETRY_OPERATION
            ),
            reason_code="retry",
            summary="Retry.",
            confidence=0.8,
            actions=(_retry_action(),),
            planned_target_refs=(
                "operation-1",
            ),
            deferred_target_refs=(
                "operation-1",
            ),
        )


def test_plan_rejects_automatic_action_without_permission():
    action = _retry_action().model_copy(
        update={
            "automatic_execution_allowed": True,
        }
    )

    with pytest.raises(
        ValidationError,
        match="requires plan automatic",
    ):
        ObjectiveRepairPlan(
            repair_request_ref="request-1",
            objective=_objective(),
            disposition=(
                ObjectiveRepairDisposition
                .RETRY_OPERATION
            ),
            reason_code="retry",
            summary="Retry.",
            confidence=0.8,
            actions=(action,),
            planned_target_refs=(
                "operation-1",
            ),
            automatic_execution_allowed=False,
        )
