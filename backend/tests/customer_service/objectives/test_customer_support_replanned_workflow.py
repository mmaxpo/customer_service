from __future__ import annotations

import pytest

from app.domains.customer_service.services.support.repair.workflow import (
    CustomerSupportRepairWorkflowBuilder,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewOperation,
    SupportReviewOperationType,
    SupportReviewPlan,
)
from app.runtime.nodes.configs import (
    HumanApprovalConfig,
    JoinAllConfig,
    ResponseConfig,
    RouterRulesConfig,
    SetVariableConfig,
)
from app.runtime.engine.validator import (
    validate_workflow,
)
from app.runtime.nodes.builtins.capability import (
    CapabilityInvokeConfig,
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


def _repair_plan() -> ObjectiveRepairPlan:
    actions = (
        ObjectiveRepairAction(
            action_ref="repair-action-refund",
            disposition=(
                ObjectiveRepairDisposition
                .REPLAN_REMAINING
            ),
            target_operation_refs=(
                "refund-operation",
            ),
            reason_code=(
                "support_operation_failed_requires_replan"
            ),
            summary=(
                "Rebuild failed refund operation."
            ),
            confidence=0.9,
            automatic_execution_allowed=False,
            human_approval_required=True,
        ),
        ObjectiveRepairAction(
            action_ref="repair-action-replacement",
            disposition=(
                ObjectiveRepairDisposition
                .REPLAN_REMAINING
            ),
            target_operation_refs=(
                "replacement-operation",
            ),
            reason_code=(
                "support_operation_failed_requires_replan"
            ),
            summary=(
                "Rebuild failed replacement operation."
            ),
            confidence=0.9,
            automatic_execution_allowed=False,
            human_approval_required=True,
        ),
    )

    return ObjectiveRepairPlan(
        repair_request_ref="repair-request-1",
        objective=ObjectiveReference(
            namespace="customer_service.support",
            objective_type="multi_operation",
            objective_ref="review-plan-1",
            objective_version=1,
        ),
        disposition=(
            ObjectiveRepairDisposition
            .REPLAN_REMAINING
        ),
        reason_code=(
            "support_repair_requires_replanning"
        ),
        summary="Replan failed operations.",
        confidence=0.9,
        actions=actions,
        planned_target_refs=(
            "refund-operation",
            "replacement-operation",
        ),
        deferred_target_refs=(),
        unhandled_target_refs=(),
        automatic_execution_allowed=False,
        human_approval_required=True,
    )


def _repair_review_plan() -> SupportReviewPlan:
    return SupportReviewPlan(
        order_ref="#1001",
        provider="shopify",
        provider_order_id=(
            "gid://shopify/Order/1001"
        ),
        operations=[
            SupportReviewOperation(
                operation_ref="refund-operation",
                operation_type=(
                    SupportReviewOperationType
                    .PARTIAL_REFUND
                ),
                item_id="refund-line",
                item_label="Snowboard",
                approval_required=True,
                execution_allowed=False,
            ),
            SupportReviewOperation(
                operation_ref=(
                    "replacement-operation"
                ),
                operation_type=(
                    SupportReviewOperationType
                    .REPLACEMENT
                ),
                item_id="replacement-line",
                item_label="Boots",
                approval_required=True,
                execution_allowed=False,
            ),
            SupportReviewOperation(
                operation_ref="address-operation",
                operation_type=(
                    SupportReviewOperationType
                    .REPLACEMENT_ADDRESS
                ),
                address={
                    "address1": "123 Main Street",
                    "city": "Miami",
                    "province": "FL",
                    "zip": "33101",
                    "country": "US",
                },
                approval_required=True,
                execution_allowed=False,
            ),
        ],
        approval_required=True,
        execution_allowed=False,
        source_objective_version=1,
    )


def _workflow() -> dict:
    return (
        CustomerSupportRepairWorkflowBuilder()
        .build_replanned_operations(
            repair_execution_id=(
                "repair-execution-1"
            ),
            resolution_record_id="resolution-1",
            attempt_number=2,
            repair_plan=_repair_plan(),
            repair_review_plan=(
                _repair_review_plan()
            ),
        )
    )


def _node(
    workflow: dict,
    node_id: str,
) -> dict:
    return next(
        node
        for node in workflow["nodes"]
        if node["id"] == node_id
    )


def test_requires_new_approval_before_provider_nodes():
    workflow = _workflow()

    approval = _node(
        workflow,
        "repair_approval",
    )

    assert (
        approval["data"]["nodeType"]
        == "human.approval"
    )

    assert {
        "source": "route_repair_approval",
        "target": (
            "set_approved_repair_context"
        ),
        "condition": "approved",
    } in workflow["edges"]

    for node_id in (
        "repair_prepare_partial_refund",
        "repair_prepare_replacement",
    ):
        assert {
            "source": (
                "set_approved_repair_context"
            ),
            "target": node_id,
        } in workflow["edges"]


def test_provider_keys_are_scoped_to_repair_execution():
    workflow = _workflow()

    refund = _node(
        workflow,
        "repair_prepare_partial_refund",
    )["data"]["config"]["payload"]

    replacement = _node(
        workflow,
        "repair_prepare_replacement",
    )["data"]["config"]["payload"]

    assert refund["idempotency_key"] == (
        "support-repair:"
        "repair-execution-1:"
        "refund-operation"
    )

    assert replacement["idempotency_key"] == (
        "support-repair:"
        "repair-execution-1:"
        "replacement-operation"
    )


def test_provider_metadata_preserves_operation_lineage():
    workflow = _workflow()

    refund = _node(
        workflow,
        "repair_prepare_partial_refund",
    )

    assert refund["data"]["metadata"][
        "support_operation_ref"
    ] == "refund-operation"

    assert refund["data"]["metadata"][
        "automatic_execution_allowed"
    ] is False


def test_rejected_branch_performs_no_provider_mutation():
    workflow = _workflow()

    assert {
        "source": "route_repair_approval",
        "target": "set_repair_rejected_result",
        "condition": "rejected",
    } in workflow["edges"]

    rejected = _node(
        workflow,
        "set_repair_rejected_result",
    )

    assert rejected["data"]["value"][
        "provider_mutation_performed"
    ] is False


def test_workflow_does_not_record_support_outcome():
    workflow = _workflow()

    node_types = {
        node["data"]["nodeType"]
        for node in workflow["nodes"]
    }

    assert (
        "customer_service."
        "project_support_outcome"
        not in node_types
    )

    assert (
        "customer_service."
        "record_support_outcome"
        not in node_types
    )

    assert "reply.customer_chat" not in node_types

    assert workflow["metadata"][
        "records_support_outcome"
    ] is False

    assert workflow["metadata"][
        "delivers_customer_message"
    ] is False


def test_replacement_preserves_approved_address():
    workflow = _workflow()

    replacement = _node(
        workflow,
        "repair_prepare_replacement",
    )["data"]["config"]["payload"]

    assert replacement["scope"][
        "replacement_line_item_id"
    ] == "replacement-line"

    assert replacement["scope"][
        "new_address"
    ] == {
        "address1": "123 Main Street",
        "city": "Miami",
        "province": "FL",
        "zip": "33101",
        "country": "US",
    }


def test_result_joins_lineage_and_provider_results():
    workflow = _workflow()

    assert {
        "source": (
            "set_approved_repair_context"
        ),
        "target": "join_repair_result",
    } in workflow["edges"]

    assert {
        "source": (
            "join_repair_operation_results"
        ),
        "target": "join_repair_result",
    } in workflow["edges"]

    response = _node(
        workflow,
        "approved_repair_response",
    )

    assert response["data"]["answer_key"] == (
        "repair_result"
    )


def test_generated_workflow_validates():
    errors = validate_workflow(_workflow())

    assert errors == []


def test_generated_builtin_configs_validate():
    workflow = _workflow()

    validators = {
        "context.extract": ContextExtractConfig,
        "human.approval": HumanApprovalConfig,
        "router.rules": RouterRulesConfig,
        "set.variable": SetVariableConfig,
        "capability.invoke": CapabilityInvokeConfig,
        "join.all": JoinAllConfig,
        "response": ResponseConfig,
    }

    for node in workflow["nodes"]:
        node_type = node["data"]["nodeType"]
        validator = validators.get(node_type)

        if validator is not None:
            validator.model_validate(
                node["data"]
            )


def test_automatic_execution_plan_is_rejected():
    plan = _repair_plan().model_copy(
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
            .build_replanned_operations(
                repair_execution_id=(
                    "repair-execution-1"
                ),
                resolution_record_id=(
                    "resolution-1"
                ),
                attempt_number=1,
                repair_plan=plan,
                repair_review_plan=(
                    _repair_review_plan()
                ),
            )
        )


def test_non_replan_action_is_rejected():
    action = _repair_plan().actions[0].model_copy(
        update={
            "disposition": (
                ObjectiveRepairDisposition
                .WAIT_FOR_RESULT
            ),
            "human_approval_required": False,
            "wait_for_event_type": (
                "customer_service.support."
                "operation.status_changed"
            ),
        }
    )

    plan = _repair_plan().model_copy(
        update={
            "actions": (action,),
            "planned_target_refs": (
                "refund-operation",
            ),
        }
    )

    with pytest.raises(
        ValueError,
        match="non-replan repair actions",
    ):
        (
            CustomerSupportRepairWorkflowBuilder()
            .build_replanned_operations(
                repair_execution_id=(
                    "repair-execution-1"
                ),
                resolution_record_id=(
                    "resolution-1"
                ),
                attempt_number=1,
                repair_plan=plan,
                repair_review_plan=(
                    _repair_review_plan()
                ),
            )
        )


def test_unblocked_review_plan_is_rejected():
    plan = _repair_review_plan()
    plan.execution_allowed = True

    with pytest.raises(
        ValueError,
        match="execution-blocked",
    ):
        (
            CustomerSupportRepairWorkflowBuilder()
            .build_replanned_operations(
                repair_execution_id=(
                    "repair-execution-1"
                ),
                resolution_record_id=(
                    "resolution-1"
                ),
                attempt_number=1,
                repair_plan=_repair_plan(),
                repair_review_plan=plan,
            )
        )
