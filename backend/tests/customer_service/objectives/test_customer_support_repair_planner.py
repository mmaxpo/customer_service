from __future__ import annotations

from copy import deepcopy

import pytest

from app.domains.customer_service.services.support.repair.planner import (
    CUSTOMER_SUPPORT_OPERATION_STATUS_CHANGED_EVENT,
    CustomerSupportObjectiveRepairPlanner,
)
from app.domains.customer_service.services.support.repair.registry import (
    register_customer_support_repair_planners,
)
from app.runtime.objectives.repair import (
    ObjectiveRepairConstraints,
    ObjectiveRepairDisposition,
    ObjectiveRepairPlannerRegistry,
    ObjectiveRepairPlanningContext,
    ObjectiveRepairRequestBuilder,
)
from app.runtime.objectives.resolution import (
    ObjectiveOperationResolution,
    ObjectiveOperationStatus,
    ObjectiveReference,
    ObjectiveResolutionAssessment,
    ObjectiveResolutionSource,
    ObjectiveResolutionStatus,
)


ALL_DISPOSITIONS = (
    ObjectiveRepairDisposition.RETRY_OPERATION,
    ObjectiveRepairDisposition.WAIT_FOR_RESULT,
    ObjectiveRepairDisposition.REPLAN_REMAINING,
    ObjectiveRepairDisposition.REQUEST_HUMAN_ACTION,
    ObjectiveRepairDisposition.STOP_REPAIR,
)


def _assessment(
    *,
    operations,
    objective_type="multi_operation",
):
    statuses = [
        operation.status
        for operation in operations
    ]

    if ObjectiveOperationStatus.FAILED in statuses:
        status = ObjectiveResolutionStatus.FAILED
        reason_code = "one_or_more_operations_failed"
    elif (
        ObjectiveOperationStatus.ACHIEVED
        in statuses
        and any(
            item
            in {
                ObjectiveOperationStatus.PENDING,
                ObjectiveOperationStatus.UNKNOWN,
            }
            for item in statuses
        )
    ):
        status = (
            ObjectiveResolutionStatus
            .PARTIALLY_ACHIEVED
        )
        reason_code = (
            "completed_and_incomplete_operations"
        )
    elif all(
        item == ObjectiveOperationStatus.PENDING
        for item in statuses
    ):
        status = ObjectiveResolutionStatus.PROGRESSING
        reason_code = (
            "operations_prepared_or_submitted"
        )
    else:
        status = ObjectiveResolutionStatus.INCONCLUSIVE
        reason_code = "insufficient_operation_evidence"

    return ObjectiveResolutionAssessment(
        objective=ObjectiveReference(
            namespace="customer_service.support",
            objective_type=objective_type,
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
        reason_code=reason_code,
        summary="Support objective remains unresolved.",
        confidence=0.9,
        is_terminal=False,
        operations=tuple(operations),
    )


def _operation(
    *,
    operation_ref,
    operation_type,
    status,
    required=True,
):
    return ObjectiveOperationResolution(
        operation_ref=operation_ref,
        operation_type=operation_type,
        status=status,
        required=required,
        reason_code=(
            f"support_operation_{status.value}"
        ),
        summary=(
            f"{operation_type} is {status.value}."
        ),
        source_task_id=(
            f"task-{operation_ref}"
        ),
        verification_ref=(
            f"verification-{operation_ref}"
        ),
        evidence_refs=(
            f"evidence-{operation_ref}",
        ),
    )


def _context(
    *,
    operations,
    allowed=ALL_DISPOSITIONS,
    allow_automatic_execution=False,
    require_human_approval=False,
    objective_type="multi_operation",
):
    assessment = _assessment(
        operations=operations,
        objective_type=objective_type,
    )

    request = ObjectiveRepairRequestBuilder().build(
        resolution_record_ref="resolution-1",
        resolution_projection_version=1,
        assessment=assessment,
        constraints=ObjectiveRepairConstraints(
            allow_automatic_execution=(
                allow_automatic_execution
            ),
            require_human_approval=(
                require_human_approval
            ),
            allowed_dispositions=allowed,
        ),
    )

    return ObjectiveRepairPlanningContext(
        request=request,
        resolution=assessment,
    )


@pytest.mark.parametrize(
    "operation_type",
    [
        "whole_refund",
        "partial_refund",
        "replacement",
    ],
)
def test_failed_mutation_replans_with_new_approval(
    operation_type,
):
    context = _context(
        operations=(
            _operation(
                operation_ref="operation-1",
                operation_type=operation_type,
                status=(
                    ObjectiveOperationStatus.FAILED
                ),
            ),
        ),
    )

    plan = (
        CustomerSupportObjectiveRepairPlanner()
        .plan_repair(context)
    )

    action = plan.actions[0]

    assert plan.disposition == (
        ObjectiveRepairDisposition
        .REPLAN_REMAINING
    )
    assert plan.human_approval_required is True
    assert plan.automatic_execution_allowed is False

    assert action.disposition == (
        ObjectiveRepairDisposition
        .REPLAN_REMAINING
    )
    assert action.human_approval_required is True
    assert (
        action.planner_directives[
            "rebuild_only_target_operations"
        ]
        is True
    )


@pytest.mark.parametrize(
    "operation_type",
    [
        "whole_refund",
        "replacement",
        "replacement_address",
    ],
)
def test_pending_operation_waits_without_duplicate(
    operation_type,
):
    context = _context(
        operations=(
            _operation(
                operation_ref="operation-1",
                operation_type=operation_type,
                status=(
                    ObjectiveOperationStatus.PENDING
                ),
            ),
        ),
    )

    plan = (
        CustomerSupportObjectiveRepairPlanner()
        .plan_repair(context)
    )

    action = plan.actions[0]

    assert plan.disposition == (
        ObjectiveRepairDisposition
        .WAIT_FOR_RESULT
    )
    assert action.wait_for_event_type == (
        CUSTOMER_SUPPORT_OPERATION_STATUS_CHANGED_EVENT
    )
    assert (
        action.planner_directives[
            "do_not_duplicate_mutation"
        ]
        is True
    )
    assert action.human_approval_required is False


@pytest.mark.parametrize(
    "operation_type",
    [
        "whole_refund",
        "replacement",
        "replacement_address",
    ],
)
def test_unknown_operation_requires_human_verification(
    operation_type,
):
    context = _context(
        operations=(
            _operation(
                operation_ref="operation-1",
                operation_type=operation_type,
                status=(
                    ObjectiveOperationStatus.UNKNOWN
                ),
            ),
        ),
    )

    plan = (
        CustomerSupportObjectiveRepairPlanner()
        .plan_repair(context)
    )

    action = plan.actions[0]

    assert plan.disposition == (
        ObjectiveRepairDisposition
        .REQUEST_HUMAN_ACTION
    )
    assert plan.human_approval_required is True
    assert action.human_approval_required is True
    assert (
        action.planner_directives[
            "verify_external_state"
        ]
        is True
    )


def test_mixed_targets_create_deterministic_actions():
    context = _context(
        operations=(
            _operation(
                operation_ref="refund",
                operation_type="whole_refund",
                status=(
                    ObjectiveOperationStatus.FAILED
                ),
            ),
            _operation(
                operation_ref="replacement",
                operation_type="replacement",
                status=(
                    ObjectiveOperationStatus.PENDING
                ),
            ),
            _operation(
                operation_ref="address",
                operation_type="replacement_address",
                status=(
                    ObjectiveOperationStatus.UNKNOWN
                ),
            ),
        ),
    )

    planner = CustomerSupportObjectiveRepairPlanner()

    first = planner.plan_repair(context)
    second = planner.plan_repair(context)

    assert first == second

    assert [
        action.disposition
        for action in first.actions
    ] == [
        ObjectiveRepairDisposition.REPLAN_REMAINING,
        ObjectiveRepairDisposition.WAIT_FOR_RESULT,
        (
            ObjectiveRepairDisposition
            .REQUEST_HUMAN_ACTION
        ),
    ]

    assert first.disposition == (
        ObjectiveRepairDisposition
        .REQUEST_HUMAN_ACTION
    )

    assert first.planned_target_refs == (
        "refund",
        "replacement",
        "address",
    )

    assert len(
        {
            action.action_ref
            for action in first.actions
        }
    ) == 3


def test_achieved_operation_is_not_replanned():
    context = _context(
        operations=(
            _operation(
                operation_ref="completed-refund",
                operation_type="whole_refund",
                status=(
                    ObjectiveOperationStatus.ACHIEVED
                ),
            ),
            _operation(
                operation_ref="failed-replacement",
                operation_type="replacement",
                status=(
                    ObjectiveOperationStatus.FAILED
                ),
            ),
        ),
    )

    plan = (
        CustomerSupportObjectiveRepairPlanner()
        .plan_repair(context)
    )

    assert plan.planned_target_refs == (
        "failed-replacement",
    )

    assert all(
        "completed-refund"
        not in action.target_operation_refs
        for action in plan.actions
    )


def test_unsupported_operation_requires_human_action():
    context = _context(
        operations=(
            _operation(
                operation_ref="cancel-1",
                operation_type="cancel_order",
                status=(
                    ObjectiveOperationStatus.FAILED
                ),
            ),
        ),
    )

    action = (
        CustomerSupportObjectiveRepairPlanner()
        .plan_repair(context)
        .actions[0]
    )

    assert action.disposition == (
        ObjectiveRepairDisposition
        .REQUEST_HUMAN_ACTION
    )
    assert action.reason_code == (
        "unsupported_support_operation_type"
    )


def test_automatic_execution_is_never_granted():
    context = _context(
        operations=(
            _operation(
                operation_ref="operation-1",
                operation_type="replacement",
                status=(
                    ObjectiveOperationStatus.FAILED
                ),
            ),
        ),
        allow_automatic_execution=True,
    )

    plan = (
        CustomerSupportObjectiveRepairPlanner()
        .plan_repair(context)
    )

    assert plan.automatic_execution_allowed is False

    assert all(
        action.automatic_execution_allowed is False
        for action in plan.actions
    )


def test_disallowed_wait_falls_back_to_human():
    context = _context(
        operations=(
            _operation(
                operation_ref="operation-1",
                operation_type="replacement",
                status=(
                    ObjectiveOperationStatus.PENDING
                ),
            ),
        ),
        allowed=(
            ObjectiveRepairDisposition
            .REQUEST_HUMAN_ACTION,
            ObjectiveRepairDisposition.STOP_REPAIR,
        ),
    )

    plan = (
        CustomerSupportObjectiveRepairPlanner()
        .plan_repair(context)
    )

    assert plan.actions[0].disposition == (
        ObjectiveRepairDisposition
        .REQUEST_HUMAN_ACTION
    )


def test_human_disallowed_falls_back_to_stop():
    context = _context(
        operations=(
            _operation(
                operation_ref="operation-1",
                operation_type="replacement",
                status=(
                    ObjectiveOperationStatus.UNKNOWN
                ),
            ),
        ),
        allowed=(
            ObjectiveRepairDisposition.STOP_REPAIR,
        ),
    )

    plan = (
        CustomerSupportObjectiveRepairPlanner()
        .plan_repair(context)
    )

    assert plan.disposition == (
        ObjectiveRepairDisposition.STOP_REPAIR
    )
    assert plan.actions[0].disposition == (
        ObjectiveRepairDisposition.STOP_REPAIR
    )


def test_no_safe_allowed_disposition_is_rejected():
    context = _context(
        operations=(
            _operation(
                operation_ref="operation-1",
                operation_type="replacement",
                status=(
                    ObjectiveOperationStatus.UNKNOWN
                ),
            ),
        ),
        allowed=(
            ObjectiveRepairDisposition.RETRY_OPERATION,
        ),
    )

    with pytest.raises(
        ValueError,
        match="does not allow a safe disposition",
    ):
        (
            CustomerSupportObjectiveRepairPlanner()
            .plan_repair(context)
        )


def test_objective_mismatch_is_rejected():
    context = _context(
        operations=(
            _operation(
                operation_ref="operation-1",
                operation_type="replacement",
                status=(
                    ObjectiveOperationStatus.FAILED
                ),
            ),
        ),
    )

    bad_resolution = (
        context.resolution.model_copy(
            update={
                "objective": (
                    context.resolution
                    .objective.model_copy(
                        update={
                            "objective_ref": "other-review",
                        }
                    )
                ),
            }
        )
    )

    bad_context = ObjectiveRepairPlanningContext(
        request=context.request,
        resolution=bad_resolution,
    )

    with pytest.raises(
        ValueError,
        match="objective does not match",
    ):
        (
            CustomerSupportObjectiveRepairPlanner()
            .plan_repair(bad_context)
        )


def test_outcome_lineage_mismatch_is_rejected():
    context = _context(
        operations=(
            _operation(
                operation_ref="operation-1",
                operation_type="replacement",
                status=(
                    ObjectiveOperationStatus.FAILED
                ),
            ),
        ),
    )

    bad_resolution = context.resolution.model_copy(
        update={
            "source": (
                context.resolution.source.model_copy(
                    update={
                        "outcome_ref": "other-outcome",
                    }
                )
            ),
        }
    )

    with pytest.raises(
        ValueError,
        match="outcome lineage",
    ):
        (
            CustomerSupportObjectiveRepairPlanner()
            .plan_repair(
                ObjectiveRepairPlanningContext(
                    request=context.request,
                    resolution=bad_resolution,
                )
            )
        )


def test_evaluation_lineage_mismatch_is_rejected():
    context = _context(
        operations=(
            _operation(
                operation_ref="operation-1",
                operation_type="replacement",
                status=(
                    ObjectiveOperationStatus.FAILED
                ),
            ),
        ),
    )

    bad_resolution = context.resolution.model_copy(
        update={
            "source": (
                context.resolution.source.model_copy(
                    update={
                        "evaluation_ref": (
                            "other-evaluation"
                        ),
                    }
                )
            ),
        }
    )

    with pytest.raises(
        ValueError,
        match="evaluation lineage",
    ):
        (
            CustomerSupportObjectiveRepairPlanner()
            .plan_repair(
                ObjectiveRepairPlanningContext(
                    request=context.request,
                    resolution=bad_resolution,
                )
            )
        )


def test_target_set_mismatch_is_rejected():
    context = _context(
        operations=(
            _operation(
                operation_ref="operation-1",
                operation_type="replacement",
                status=(
                    ObjectiveOperationStatus.FAILED
                ),
            ),
        ),
    )

    request_data = context.request.model_dump(
        mode="python"
    )
    request_data["targets"][0][
        "operation_ref"
    ] = "other-operation"

    bad_request = (
        context.request.__class__.model_validate(
            request_data
        )
    )

    with pytest.raises(
        ValueError,
        match="targets do not match",
    ):
        (
            CustomerSupportObjectiveRepairPlanner()
            .plan_repair(
                ObjectiveRepairPlanningContext(
                    request=bad_request,
                    resolution=context.resolution,
                )
            )
        )


def test_unsupported_namespace_is_rejected():
    context = _context(
        operations=(
            _operation(
                operation_ref="operation-1",
                operation_type="replacement",
                status=(
                    ObjectiveOperationStatus.FAILED
                ),
            ),
        ),
    )

    request_data = deepcopy(
        context.request.model_dump(
            mode="python"
        )
    )

    request_data["source"]["objective"][
        "namespace"
    ] = "other.product"

    bad_request = (
        context.request.__class__.model_validate(
            request_data
        )
    )

    with pytest.raises(
        ValueError,
        match="unsupported objective namespace",
    ):
        (
            CustomerSupportObjectiveRepairPlanner()
            .plan_repair(
                ObjectiveRepairPlanningContext(
                    request=bad_request,
                    resolution=context.resolution,
                )
            )
        )


@pytest.mark.parametrize(
    "objective_type",
    [
        "support_resolution",
        "multi_operation",
    ],
)
def test_registry_resolves_customer_support_planner(
    objective_type,
):
    registry = ObjectiveRepairPlannerRegistry()

    register_customer_support_repair_planners(
        registry
    )

    planner = registry.resolve(
        namespace="customer_service.support",
        objective_type=objective_type,
    )

    assert isinstance(
        planner,
        CustomerSupportObjectiveRepairPlanner,
    )


def test_registry_registers_expected_keys():
    registry = ObjectiveRepairPlannerRegistry()

    register_customer_support_repair_planners(
        registry
    )

    assert registry.registered_keys() == (
        (
            "customer_service.support",
            "multi_operation",
        ),
        (
            "customer_service.support",
            "support_resolution",
        ),
    )


def test_duplicate_product_registration_is_rejected():
    registry = ObjectiveRepairPlannerRegistry()

    register_customer_support_repair_planners(
        registry
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        register_customer_support_repair_planners(
            registry
        )
