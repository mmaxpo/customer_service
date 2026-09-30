from app.domains.customer_service.services.shopify_order_context import (
    ShopifyOrderContextBuilder,
)
from app.domains.customer_service.services.shopify_support_orchestrator import (
    ShopifySupportWorkflowOrchestrator,
)


def _context(order):
    return ShopifyOrderContextBuilder().build(order)


def test_orchestrator_returns_reply_ready_for_shipping_status_with_tracking():
    result = ShopifySupportWorkflowOrchestrator().handle(
        workflow_type="track_order",
        order_context=_context(
            {
                "id": "1001",
                "name": "#1001",
                "email": "customer@example.com",
                "fulfillment_status": "fulfilled",
                "tracking_number": "TRACK123",
            }
        ),
    )

    assert result["workflow_type"] == "shipping_status"
    assert result["next_action"] == "reply_ready"
    assert result["requires_approval"] is False
    assert result["order"]["order_name"] == "#1001"
    assert result["decision"]["tracking"]["tracking_number"] == "TRACK123"


def test_orchestrator_requires_approval_for_refund():
    result = ShopifySupportWorkflowOrchestrator().handle(
        workflow_type="refund_request",
        order_context=_context(
            {
                "id": "1002",
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
            }
        ),
        reason="customer requested refund",
    )

    assert result["workflow_type"] == "refund"
    assert result["next_action"] == "approval_required"
    assert result["requires_approval"] is True
    assert result["decision"]["status"] == "needs_approval"


def test_orchestrator_blocks_cancel_for_fulfilled_order():
    result = ShopifySupportWorkflowOrchestrator().handle(
        workflow_type="cancel_order",
        order_context=_context(
            {
                "id": "1003",
                "fulfillment_status": "fulfilled",
            }
        ),
    )

    assert result["workflow_type"] == "cancel"
    assert result["next_action"] == "blocked"
    assert result["decision"]["status"] == "blocked"


def test_orchestrator_requests_more_information_for_missing_address():
    result = ShopifySupportWorkflowOrchestrator().handle(
        workflow_type="address_change",
        order_context=_context(
            {
                "id": "1004",
                "fulfillment_status": "unfulfilled",
            }
        ),
    )

    assert result["workflow_type"] == "change_address"
    assert result["next_action"] == "request_more_information"
    assert result["decision"]["status"] == "needs_information"


def test_orchestrator_routes_damaged_product_to_approval():
    result = ShopifySupportWorkflowOrchestrator().handle(
        workflow_type="damaged_product",
        order_context=_context(
            {
                "id": "1005",
                "financial_status": "paid",
            }
        ),
        reason="broken item",
    )

    assert result["workflow_type"] == "damaged_item"
    assert result["next_action"] == "approval_required"
    assert result["decision"]["status"] == "needs_approval"


def test_orchestrator_unsupported_workflow_goes_to_manual_review():
    result = ShopifySupportWorkflowOrchestrator().handle(
        workflow_type="unknown",
        order_context=_context({"id": "1006"}),
    )

    assert result["workflow_type"] == "unknown"
    assert result["next_action"] == "manual_review"
    assert result["decision"]["status"] == "unsupported"
