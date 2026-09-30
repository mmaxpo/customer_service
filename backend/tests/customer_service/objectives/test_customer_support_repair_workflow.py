from __future__ import annotations

import pytest

from app.domains.customer_service.services.support.repair.workflow import (
    CustomerSupportRepairWorkflowBuilder,
)
from app.runtime.nodes.configs import (
    HumanApprovalConfig,
    ResponseConfig,
    SetVariableConfig,
    WaitEventConfig,
)
from app.runtime.nodes.builtins.context_extract import (
    ContextExtractConfig,
)
from app.runtime.objectives.repair import (
    ObjectiveRepairAction,
    ObjectiveRepairDisposition,
    ObjectiveRepairPlan,
)
from app.runtime.objectives.resolution import (
    ObjectiveReference,
)


def _action(
    *,
    action_ref: str,
    disposition: ObjectiveRepairDisposition,
    operation_ref: str,
) -> ObjectiveRepairAction:
    kwargs = {}

    if (
        disposition
        == ObjectiveRepairDisposition
        .WAIT_FOR_RESULT
    ):
        kwargs["wait_for_event_type"] = (
            "customer_service.support."
            "operation.status_changed"
        )

    return ObjectiveRepairAction(
        action_ref=action_ref,
        disposition=disposition,
        target_operation_refs=(
            operation_ref,
        ),
        reason_code="test_repair_action",
        summary=(
            "Review or wait for this operation."
        ),
        confidence=0.9,
        automatic_execution_allowed=False,
        human_approval_required=(
            disposition
            == ObjectiveRepairDisposition
            .REQUEST_HUMAN_ACTION
        ),
        metadata={
            "source_task_id": (
                f"task-{operation_ref}"
            ),
            "verification_ref": (
                f"verification-{operation_ref}"
            ),
        },
        **kwargs,
    )


def _plan(
    *actions: ObjectiveRepairAction,
) -> ObjectiveRepairPlan:
    return ObjectiveRepairPlan(
        repair_request_ref="repair-request-1",
        objective=ObjectiveReference(
            namespace="customer_service.support",
            objective_type="multi_operation",
            objective_ref="review-1",
            objective_version=1,
        ),
        disposition=actions[0].disposition,
        reason_code="test_repair_plan",
        summary="Test non-mutating repair plan.",
        confidence=0.9,
        actions=actions,
        planned_target_refs=tuple(
            action.target_operation_refs[0]
            for action in actions
        ),
        deferred_target_refs=(),
        unhandled_target_refs=(),
        automatic_execution_allowed=False,
        human_approval_required=any(
            action.human_approval_required
            for action in actions
        ),
    )


def _node(workflow: dict, node_id: str) -> dict:
    return next(
        node
        for node in workflow["nodes"]
        if node["id"] == node_id
    )


def test_wait_action_uses_correlated_event_wait():
    workflow = (
        CustomerSupportRepairWorkflowBuilder()
        .build_non_mutating(
            repair_execution_id="repair-execution-1",
            resolution_record_id="resolution-1",
            attempt_number=1,
            repair_plan=_plan(
                _action(
                    action_ref="wait-action",
                    disposition=(
                        ObjectiveRepairDisposition
                        .WAIT_FOR_RESULT
                    ),
                    operation_ref="operation-1",
                )
            ),
        )
    )

    wait = _node(
        workflow,
        "repair_action_001_wait",
    )

    config = WaitEventConfig.model_validate(
        wait["data"]
    )

    assert config.event_type == (
        "customer_service.support."
        "operation.status_changed"
    )
    assert config.match == {
        "repair_execution_id": (
            "repair-execution-1"
        ),
        "resolution_record_id": (
            "resolution-1"
        ),
        "operation_ref": "operation-1",
    }


def test_human_action_includes_durable_context():
    workflow = (
        CustomerSupportRepairWorkflowBuilder()
        .build_non_mutating(
            repair_execution_id="repair-execution-1",
            resolution_record_id="resolution-1",
            attempt_number=1,
            repair_plan=_plan(
                _action(
                    action_ref="human-action",
                    disposition=(
                        ObjectiveRepairDisposition
                        .REQUEST_HUMAN_ACTION
                    ),
                    operation_ref="operation-1",
                )
            ),
        )
    )

    node = _node(
        workflow,
        "repair_action_001_human_review",
    )

    config = HumanApprovalConfig.model_validate(
        node["data"]
    )

    assert config.context_key == (
        "objective_repair"
    )
    assert config.context_payload_key == (
        "repair_context"
    )
    assert config.save_as == (
        "repair_action_001_approved"
    )


def test_stop_action_never_invokes_provider():
    workflow = (
        CustomerSupportRepairWorkflowBuilder()
        .build_non_mutating(
            repair_execution_id="repair-execution-1",
            resolution_record_id="resolution-1",
            attempt_number=1,
            repair_plan=_plan(
                _action(
                    action_ref="stop-action",
                    disposition=(
                        ObjectiveRepairDisposition
                        .STOP_REPAIR
                    ),
                    operation_ref="operation-1",
                )
            ),
        )
    )

    node_types = {
        node["data"]["nodeType"]
        for node in workflow["nodes"]
    }

    assert "capability.invoke" not in node_types
    assert "shopify.order_action" not in node_types
    assert "reply.customer_chat" not in node_types
    assert (
        "customer_service."
        "record_support_outcome"
        not in node_types
    )

    stop = _node(
        workflow,
        "repair_action_001_stop",
    )

    SetVariableConfig.model_validate(
        stop["data"]
    )


def test_workflow_does_not_require_chat_session():
    workflow = (
        CustomerSupportRepairWorkflowBuilder()
        .build_non_mutating(
            repair_execution_id="repair-execution-1",
            resolution_record_id="resolution-1",
            attempt_number=1,
            repair_plan=_plan(
                _action(
                    action_ref="stop-action",
                    disposition=(
                        ObjectiveRepairDisposition
                        .STOP_REPAIR
                    ),
                    operation_ref="operation-1",
                )
            ),
        )
    )

    assert all(
        not (
            node["data"].get("nodeType")
            == "context.extract"
            and node["data"].get("path")
            == "session_id"
        )
        for node in workflow["nodes"]
    )


def test_generated_builtin_configs_validate():
    workflow = (
        CustomerSupportRepairWorkflowBuilder()
        .build_non_mutating(
            repair_execution_id="repair-execution-1",
            resolution_record_id="resolution-1",
            attempt_number=2,
            repair_plan=_plan(
                _action(
                    action_ref="wait-action",
                    disposition=(
                        ObjectiveRepairDisposition
                        .WAIT_FOR_RESULT
                    ),
                    operation_ref="operation-1",
                ),
                _action(
                    action_ref="human-action",
                    disposition=(
                        ObjectiveRepairDisposition
                        .REQUEST_HUMAN_ACTION
                    ),
                    operation_ref="operation-2",
                ),
                _action(
                    action_ref="stop-action",
                    disposition=(
                        ObjectiveRepairDisposition
                        .STOP_REPAIR
                    ),
                    operation_ref="operation-3",
                ),
            ),
        )
    )

    validators = {
        "context.extract": ContextExtractConfig,
        "wait.event": WaitEventConfig,
        "human.approval": HumanApprovalConfig,
        "set.variable": SetVariableConfig,
        "response": ResponseConfig,
    }

    for node in workflow["nodes"]:
        node_type = node["data"]["nodeType"]

        validator = validators.get(node_type)

        if validator is not None:
            validator.model_validate(
                node["data"]
            )


def test_action_lineage_is_preserved_in_metadata():
    workflow = (
        CustomerSupportRepairWorkflowBuilder()
        .build_non_mutating(
            repair_execution_id="repair-execution-1",
            resolution_record_id="resolution-1",
            attempt_number=3,
            repair_plan=_plan(
                _action(
                    action_ref="human-action",
                    disposition=(
                        ObjectiveRepairDisposition
                        .REQUEST_HUMAN_ACTION
                    ),
                    operation_ref="operation-1",
                )
            ),
        )
    )

    metadata = _node(
        workflow,
        "repair_action_001_human_review",
    )["data"]["metadata"]

    assert metadata == {
        "repair_action_ref": "human-action",
        "disposition": "request_human_action",
        "target_operation_refs": [
            "operation-1"
        ],
        "reason_code": "test_repair_action",
        "repair_execution_id": (
            "repair-execution-1"
        ),
        "resolution_record_id": (
            "resolution-1"
        ),
        "attempt_number": 3,
        "source_task_id": "task-operation-1",
        "verification_ref": (
            "verification-operation-1"
        ),
    }


def test_extras_include_full_repair_plan():
    plan = _plan(
        _action(
            action_ref="stop-action",
            disposition=(
                ObjectiveRepairDisposition.STOP_REPAIR
            ),
            operation_ref="operation-1",
        )
    )

    extras = (
        CustomerSupportRepairWorkflowBuilder
        .objective_repair_extras(
            repair_execution_id="repair-execution-1",
            resolution_record_id="resolution-1",
            attempt_number=1,
            repair_plan=plan,
        )
    )

    assert extras["repair_execution_id"] == (
        "repair-execution-1"
    )
    assert extras["repair_plan"] == (
        plan.model_dump(mode="json")
    )


def test_workflow_job_key_is_deterministic():
    first = (
        CustomerSupportRepairWorkflowBuilder
        .workflow_job_idempotency_key(
            repair_execution_id=(
                "repair-execution-1"
            )
        )
    )

    second = (
        CustomerSupportRepairWorkflowBuilder
        .workflow_job_idempotency_key(
            repair_execution_id=(
                "repair-execution-1"
            )
        )
    )

    assert first == second
    assert first == (
        "customer-support-repair-workflow:"
        "repair-execution-1:workflow-v1"
    )


def test_replan_action_is_rejected_by_non_mutating_builder():
    action = ObjectiveRepairAction(
        action_ref="replan-action",
        disposition=(
            ObjectiveRepairDisposition
            .REPLAN_REMAINING
        ),
        target_operation_refs=("operation-1",),
        reason_code="repair_replan",
        summary="Replan failed operation.",
        confidence=0.9,
        automatic_execution_allowed=False,
        human_approval_required=True,
    )

    with pytest.raises(
        ValueError,
        match="provider-operation repair actions",
    ):
        (
            CustomerSupportRepairWorkflowBuilder()
            .build_non_mutating(
                repair_execution_id=(
                    "repair-execution-1"
                ),
                resolution_record_id=(
                    "resolution-1"
                ),
                attempt_number=1,
                repair_plan=_plan(action),
            )
        )


def test_automatic_execution_plan_is_rejected():
    plan = _plan(
        _action(
            action_ref="stop-action",
            disposition=(
                ObjectiveRepairDisposition.STOP_REPAIR
            ),
            operation_ref="operation-1",
        )
    ).model_copy(
        update={
            "automatic_execution_allowed": True,
        }
    )

    with pytest.raises(
        ValueError,
        match="cannot allow automatic execution",
    ):
        (
            CustomerSupportRepairWorkflowBuilder()
            .build_non_mutating(
                repair_execution_id=(
                    "repair-execution-1"
                ),
                resolution_record_id=(
                    "resolution-1"
                ),
                attempt_number=1,
                repair_plan=plan,
            )
        )
