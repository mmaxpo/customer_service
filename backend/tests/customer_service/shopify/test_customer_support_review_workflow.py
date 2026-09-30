import pytest

from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewOperation,
    SupportReviewOperationType,
    SupportReviewPlan,
)
from app.domains.customer_service.services.support.planning.customer_support_review_workflow import (
    CustomerSupportReviewWorkflowBuilder,
)


def _plan() -> SupportReviewPlan:
    return SupportReviewPlan(
        order_ref="#1003",
        provider="shopify",
        provider_order_id="gid://shopify/Order/1003",
        operations=[
            SupportReviewOperation(
                operation_type=(
                    SupportReviewOperationType.PARTIAL_REFUND
                ),
                item_id="line-item-refund",
                item_label="Blue Shirt",
            ),
            SupportReviewOperation(
                operation_type=(
                    SupportReviewOperationType.REPLACEMENT
                ),
                item_id="line-item-replacement",
                item_label="Black Shoes",
            ),
            SupportReviewOperation(
                operation_type=(
                    SupportReviewOperationType.REPLACEMENT_ADDRESS
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
    )


def _node(workflow: dict, node_id: str) -> dict:
    return next(
        node
        for node in workflow["nodes"]
        if node["id"] == node_id
    )


def test_review_workflow_requires_human_approval_before_actions():
    workflow = CustomerSupportReviewWorkflowBuilder().build(
        review_plan_id="review-123",
        review_plan=_plan(),
    )

    approval = _node(workflow, "approval")
    refund = _node(workflow, "prepare_partial_refund")
    replacement = _node(workflow, "prepare_replacement")

    assert approval["data"]["nodeType"] == "human.approval"
    assert approval["data"]["context_key"] == "support_review"

    assert (
        refund["data"]["config"]["capability_id"]
        == "ecommerce.orders.action"
    )
    assert (
        replacement["data"]["config"]["capability_id"]
        == "ecommerce.orders.action"
    )

    assert {
        "source": "route_approval",
        "target": "prepare_partial_refund",
        "condition": "approved",
    } in workflow["edges"]

    assert {
        "source": "route_approval",
        "target": "prepare_replacement",
        "condition": "approved",
    } in workflow["edges"]


def test_refund_payload_preserves_exact_item_scope():
    workflow = CustomerSupportReviewWorkflowBuilder().build(
        review_plan_id="review-123",
        review_plan=_plan(),
    )

    refund = _node(
        workflow,
        "prepare_partial_refund",
    )["data"]["config"]["payload"]

    assert refund["action"] == "refund"
    assert refund["order_ref"] == "#1003"
    assert refund["scope"]["line_items"] == [
        {
            "line_item_id": "line-item-refund",
            "quantity": 1,
            "amount": None,
        }
    ]
    assert refund["idempotency_key"] == (
        "support-review:review-123:partial-refund"
    )


def test_replacement_payload_includes_approved_new_address():
    workflow = CustomerSupportReviewWorkflowBuilder().build(
        review_plan_id="review-123",
        review_plan=_plan(),
    )

    replacement = _node(
        workflow,
        "prepare_replacement",
    )["data"]["config"]["payload"]

    assert replacement["action"] == "reship"
    assert (
        replacement["scope"]["replacement_line_item_id"]
        == "line-item-replacement"
    )
    assert replacement["scope"]["replacement_quantity"] == 1
    assert replacement["scope"]["new_address"] == {
        "address1": "123 Main Street",
        "city": "Miami",
        "province": "FL",
        "zip": "33101",
        "country": "US",
    }
    assert replacement["idempotency_key"] == (
        "support-review:review-123:replacement"
    )


def test_address_is_not_executed_as_original_order_mutation():
    workflow = CustomerSupportReviewWorkflowBuilder().build(
        review_plan_id="review-123",
        review_plan=_plan(),
    )

    capability_payloads = [
        node["data"]["config"]["payload"]
        for node in workflow["nodes"]
        if node["data"].get("nodeType")
        == "capability.invoke"
    ]

    assert {
        payload["action"]
        for payload in capability_payloads
    } == {
        "refund",
        "reship",
    }

    assert all(
        payload["action"] != "update_shipping_address"
        for payload in capability_payloads
    )


def test_operation_idempotency_keys_are_distinct_and_stable():
    builder = CustomerSupportReviewWorkflowBuilder()

    first = builder.build(
        review_plan_id="review-123",
        review_plan=_plan(),
    )
    second = builder.build(
        review_plan_id="review-123",
        review_plan=_plan(),
    )

    def keys(workflow):
        return [
            node["data"]["config"]["payload"][
                "idempotency_key"
            ]
            for node in workflow["nodes"]
            if node["data"].get("nodeType")
            == "capability.invoke"
        ]

    assert keys(first) == keys(second)
    assert len(set(keys(first))) == 2

    assert builder.workflow_job_idempotency_key(
        review_plan_id="review-123",
    ) == (
        "customer-support-review-workflow:"
        "review-123:v1"
    )


def test_builder_rejects_plan_without_executable_operation():
    plan = SupportReviewPlan(
        order_ref="#1003",
        provider="shopify",
        operations=[
            SupportReviewOperation(
                operation_type=(
                    SupportReviewOperationType.REPLACEMENT_ADDRESS
                ),
                address={
                    "address1": "123 Main Street",
                },
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match="no executable preparation operation",
    ):
        CustomerSupportReviewWorkflowBuilder().build(
            review_plan_id="review-123",
            review_plan=plan,
        )



def test_whole_order_refund_runs_only_after_human_approval():
    plan = SupportReviewPlan(
        order_ref="#1001",
        provider="shopify",
        provider_order_id="gid://shopify/Order/1001",
        operations=[
            SupportReviewOperation(
                operation_type=(
                    SupportReviewOperationType.WHOLE_REFUND
                ),
            ),
        ],
    )

    workflow = CustomerSupportReviewWorkflowBuilder().build(
        review_plan_id="review-whole-refund",
        review_plan=plan,
    )

    refund = _node(workflow, "prepare_whole_refund")

    assert refund["data"]["nodeType"] == "capability.invoke"
    assert (
        refund["data"]["config"]["capability_id"]
        == "ecommerce.orders.action"
    )

    payload = refund["data"]["config"]["payload"]

    assert payload["action"] == "refund"
    assert payload["order_ref"] == "#1001"
    assert payload["amount"] is None
    assert payload["scope"] is None
    assert payload["idempotency_key"] == (
        "support-review:"
        "review-whole-refund:"
        "whole-refund"
    )

    assert {
        "source": "route_approval",
        "target": "prepare_whole_refund",
        "condition": "approved",
    } in workflow["edges"]


def test_whole_and_partial_refunds_use_distinct_idempotency_keys():
    plan = SupportReviewPlan(
        order_ref="#1001",
        provider="shopify",
        operations=[
            SupportReviewOperation(
                operation_type=(
                    SupportReviewOperationType.WHOLE_REFUND
                ),
            ),
            SupportReviewOperation(
                operation_type=(
                    SupportReviewOperationType.PARTIAL_REFUND
                ),
                item_id="line-1",
                item_label="Snowboard",
            ),
        ],
    )

    workflow = CustomerSupportReviewWorkflowBuilder().build(
        review_plan_id="review-mixed-refund",
        review_plan=plan,
    )

    whole = _node(
        workflow,
        "prepare_whole_refund",
    )["data"]["config"]["payload"]

    partial = _node(
        workflow,
        "prepare_partial_refund",
    )["data"]["config"]["payload"]

    assert whole["idempotency_key"] != partial["idempotency_key"]
    assert whole["scope"] is None
    assert partial["scope"]["line_items"] == [
        {
            "line_item_id": "line-1",
            "quantity": 1,
            "amount": None,
        }
    ]
