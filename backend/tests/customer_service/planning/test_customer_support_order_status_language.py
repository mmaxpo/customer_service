import pytest

from app.domains.customer_service.services.support.planning.customer_support_product_planner import (
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
from app.tcos.planner.runtime.planning_context import (
    PlanningContext,
)


ORDER_STATUS_MESSAGES = (
    "Where is my order #1001?",
    "Reply to this customer: Where is my order #1001?",
    "Customer wants order #1001 status",
    "What is the status of order #1001?",
    "Track order #1001",
    "Has order #1001 shipped?",
    "Check order #1001",
)


@pytest.mark.parametrize(
    "message",
    ORDER_STATUS_MESSAGES,
)
def test_customer_service_classifier_owns_order_status_language(
    message: str,
):
    result = (
        CustomerServiceMessageClassifier()
        .classify(message)
    )

    assert result.intent == SupportIntent.SHIPPING


@pytest.mark.parametrize(
    "message",
    ORDER_STATUS_MESSAGES,
)
def test_customer_service_product_planner_claims_order_status_language(
    message: str,
):
    planner = CustomerSupportProductPlanner()

    result = planner.plan(
        intent=detect_intent(text=message),
        context=PlanningContext(
            user_message=message,
        ),
    )

    assert result.claimed is True
    assert result.requires_clarification is False
    assert len(result.candidates) == 1

    candidate = result.candidates[0]

    assert (
        candidate.source
        == "customer_service_product_planner"
    )

    capability_ids = {
        ref.capability_id
        for task in candidate.business_plan.tasks
        for ref in task.required_capabilities
    }

    assert "ecommerce.orders.get" in capability_ids
    assert "shopify.get_order" not in capability_ids


def test_bare_order_reference_is_not_assumed_to_be_shipping():
    message = "Order #1001"

    classification = (
        CustomerServiceMessageClassifier()
        .classify(message)
    )

    assert classification.intent == SupportIntent.GENERAL

    result = CustomerSupportProductPlanner().plan(
        intent=detect_intent(text=message),
        context=PlanningContext(
            user_message=message,
        ),
    )

    assert result.claimed is False
