from __future__ import annotations

from app.domains.customer_service.services.support.planning.customer_support_product_planner import (
    CUSTOMER_SUPPORT_ORDER_READ_CAPABILITY,
    CUSTOMER_SUPPORT_ORDER_STATUS_CAPABILITY,
    CustomerSupportProductPlanner,
)
from app.domains.customer_service.workflows.message_classifier import (
    CustomerServiceMessageClassifier,
)
from app.domains.customer_service.workflows.schemas import (
    SupportIntent,
)
from app.tcos.planner.runtime.intent import (
    detect_intent,
)
from app.tcos.planner.runtime.planning_inputs import (
    build_default_planning_context,
)


def _plan(message: str):
    context = build_default_planning_context(
        user_message=message,
    )

    intent = detect_intent(
        text=context.user_message,
    )

    return CustomerSupportProductPlanner().plan(
        intent=intent,
        context=context,
    )


def test_existing_classifier_recognizes_not_arrived_language():
    classification = CustomerServiceMessageClassifier().classify(
        "My order hasn't arrived."
    )

    assert classification.intent == SupportIntent.SHIPPING


def test_shipping_without_order_ref_is_claimed_for_clarification():
    result = _plan(
        "My order hasn't arrived and I want to know what's happening. Check it for me."
    )

    assert result.product_id == "customer_service"
    assert result.claimed is True
    assert result.candidates == []

    assert result.requires_clarification is True
    assert result.clarification is not None

    assert result.clarification.reason_code == "missing_order_ref"

    assert result.clarification.missing_fields == ("order_ref",)

    assert "order number" in result.clarification.message.lower()

    assert result.metadata["mutation_allowed"] is False


def test_shipping_with_order_ref_builds_semantic_candidate():
    result = _plan("Reply to customer: Where is my order #1001?")

    assert result.claimed is True
    assert result.requires_clarification is False
    assert len(result.candidates) == 1

    candidate = result.candidates[0]

    assert candidate.id == "generated_customer_service_order_status"
    assert candidate.source == "customer_service_product_planner"

    assert (
        candidate.metrics["selected_capability"]
        == CUSTOMER_SUPPORT_ORDER_STATUS_CAPABILITY
    )

    assert candidate.metrics["semantic_capabilities"] == [
        CUSTOMER_SUPPORT_ORDER_READ_CAPABILITY
    ]

    assert candidate.metrics["order_ref"] == "#1001"


def test_order_status_plan_uses_provider_neutral_semantic_capability():
    result = _plan("Reply to customer: Where is my order #1001?")

    plan = result.candidates[0].business_plan

    assert plan.id == "customer_service_order_status_plan"

    assert [task.id for task in plan.tasks] == [
        "extract_order_reference",
        "lookup_order",
        "prepare_customer_answer",
        "send_customer_reply",
    ]

    assert [task.required_capabilities[0].capability_id for task in plan.tasks] == [
        "customer_service.extract_order_ref",
        "ecommerce.orders.get",
        "runtime.agent_custom",
        "runtime.response",
    ]


def test_order_status_plan_contains_no_provider_specific_identifiers():
    result = _plan("Reply to customer: Where is my order #1001?")

    payload = result.candidates[0].business_plan.model_dump_json().lower()

    assert "shopify" not in payload
    assert "wix" not in payload
    assert "woocommerce" not in payload


def test_general_customer_reply_is_claimed_by_customer_service():
    result = _plan(
        "Reply to the customer and thank them for their message."
    )

    assert result.claimed is True
    assert result.requires_clarification is False
    assert len(result.candidates) == 1

    candidate = result.candidates[0]

    assert (
        candidate.source
        == "customer_service_product_planner"
    )
    assert (
        candidate.metrics["selected_capability"]
        == "customer_service.customer_reply"
    )


def test_refund_is_not_claimed_by_order_status_slice():
    result = _plan("I want a refund for order #1001.")

    assert result.claimed is False
    assert result.candidates == []
    assert result.clarification is None
