from __future__ import annotations

import pytest

from app.domains.customer_service.services.support.planning.customer_support_operation_graph import (
    CustomerSupportOperationGraphBuilder,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewOperation,
    SupportReviewOperationType,
    SupportReviewPlan,
)
from app.runtime.nodes.builtins.capability import (
    CapabilityInvokeConfig,
)


def _review_plan() -> SupportReviewPlan:
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
                item_id="line-refund",
                item_label="Snowboard",
            ),
            SupportReviewOperation(
                operation_ref=(
                    "replacement-operation"
                ),
                operation_type=(
                    SupportReviewOperationType
                    .REPLACEMENT
                ),
                item_id="line-replacement",
                item_label="Boots",
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
            ),
        ],
        approval_required=True,
        execution_allowed=False,
    )


def _node(
    graph,
    node_id: str,
) -> dict:
    return next(
        node
        for node in graph.nodes
        if node["id"] == node_id
    )


def test_builds_partial_refund_and_replacement_nodes():
    graph = (
        CustomerSupportOperationGraphBuilder()
        .build(
            review_plan_id="review-plan-1",
            review_plan=_review_plan(),
        )
    )

    assert graph.entry_node_ids == (
        "prepare_partial_refund",
        "prepare_replacement",
    )
    assert graph.result_node_ids == (
        "prepare_partial_refund",
        "prepare_replacement",
    )

    node_types = {
        node["data"]["nodeType"]
        for node in graph.nodes
    }

    assert node_types == {
        "capability.invoke",
    }


def test_partial_refund_preserves_item_scope():
    graph = (
        CustomerSupportOperationGraphBuilder()
        .build(
            review_plan_id="review-plan-1",
            review_plan=_review_plan(),
        )
    )

    node = _node(
        graph,
        "prepare_partial_refund",
    )

    payload = node["data"]["config"]["payload"]

    assert payload["action"] == "refund"
    assert payload["order_ref"] == "#1001"
    assert payload["scope"]["line_items"] == [
        {
            "line_item_id": "line-refund",
            "quantity": 1,
            "amount": None,
        }
    ]


def test_replacement_preserves_address_scope():
    graph = (
        CustomerSupportOperationGraphBuilder()
        .build(
            review_plan_id="review-plan-1",
            review_plan=_review_plan(),
        )
    )

    node = _node(
        graph,
        "prepare_replacement",
    )

    scope = node["data"]["config"][
        "payload"
    ]["scope"]

    assert scope[
        "replacement_line_item_id"
    ] == "line-replacement"

    assert scope["new_address"] == {
        "address1": "123 Main Street",
        "city": "Miami",
        "province": "FL",
        "zip": "33101",
        "country": "US",
    }


def test_operation_ref_controls_idempotency_identity():
    graph = (
        CustomerSupportOperationGraphBuilder()
        .build(
            review_plan_id="repair-execution-1",
            review_plan=_review_plan(),
            idempotency_namespace=(
                "support-repair"
            ),
        )
    )

    refund_key = _node(
        graph,
        "prepare_partial_refund",
    )["data"]["config"]["payload"][
        "idempotency_key"
    ]

    replacement_key = _node(
        graph,
        "prepare_replacement",
    )["data"]["config"]["payload"][
        "idempotency_key"
    ]

    assert refund_key == (
        "support-repair:"
        "repair-execution-1:"
        "refund-operation"
    )

    assert replacement_key == (
        "support-repair:"
        "repair-execution-1:"
        "replacement-operation"
    )


def test_node_prefix_is_applied_consistently():
    graph = (
        CustomerSupportOperationGraphBuilder()
        .build(
            review_plan_id="review-plan-1",
            review_plan=_review_plan(),
            node_prefix="repair_attempt_2",
        )
    )

    assert graph.entry_node_ids == (
        (
            "repair_attempt_2_"
            "prepare_partial_refund"
        ),
        (
            "repair_attempt_2_"
            "prepare_replacement"
        ),
    )

    assert {
        node["data"]["config"]["save_as"]
        for node in graph.nodes
    } == {
        (
            "repair_attempt_2_"
            "partial_refund_result"
        ),
        (
            "repair_attempt_2_"
            "replacement_result"
        ),
    }


def test_generated_capability_configs_validate():
    graph = (
        CustomerSupportOperationGraphBuilder()
        .build(
            review_plan_id="review-plan-1",
            review_plan=_review_plan(),
        )
    )

    for node in graph.nodes:
        config = (
            CapabilityInvokeConfig.model_validate(
                node["data"]
            )
        )

        assert config.capability_id == (
            "ecommerce.orders.action"
        )


def test_metadata_preserves_operation_lineage():
    graph = (
        CustomerSupportOperationGraphBuilder()
        .build(
            review_plan_id="review-plan-1",
            review_plan=_review_plan(),
        )
    )

    metadata = _node(
        graph,
        "prepare_partial_refund",
    )["data"]["metadata"]

    assert metadata == {
        "support_operation_ref": (
            "refund-operation"
        ),
        "support_operation_type": (
            "partial_refund"
        ),
        "support_item_id": "line-refund",
        "support_item_label": "Snowboard",
        "approval_required": True,
        "automatic_execution_allowed": False,
    }


def test_input_plan_is_not_mutated():
    plan = _review_plan()

    graph = (
        CustomerSupportOperationGraphBuilder()
        .build(
            review_plan_id="review-plan-1",
            review_plan=plan,
        )
    )

    _node(
        graph,
        "prepare_replacement",
    )["data"]["config"]["payload"][
        "scope"
    ]["new_address"]["city"] = "Changed"

    assert (
        plan.operations[2].address["city"]
        == "Miami"
    )


def test_execution_allowed_plan_is_rejected():
    plan = _review_plan()
    plan.execution_allowed = True

    with pytest.raises(
        ValueError,
        match="execution-blocked",
    ):
        (
            CustomerSupportOperationGraphBuilder()
            .build(
                review_plan_id="review-plan-1",
                review_plan=plan,
            )
        )


def test_partial_refund_requires_item_id():
    plan = _review_plan()
    plan.operations[0].item_id = None

    with pytest.raises(
        ValueError,
        match="requires item_id",
    ):
        (
            CustomerSupportOperationGraphBuilder()
            .build(
                review_plan_id="review-plan-1",
                review_plan=plan,
            )
        )


def test_plan_without_provider_operation_is_rejected():
    plan = _review_plan()

    plan.operations = [
        operation
        for operation in plan.operations
        if operation.operation_type
        == SupportReviewOperationType
        .REPLACEMENT_ADDRESS
    ]

    with pytest.raises(
        ValueError,
        match="no executable provider operation",
    ):
        (
            CustomerSupportOperationGraphBuilder()
            .build(
                review_plan_id="review-plan-1",
                review_plan=plan,
            )
        )
