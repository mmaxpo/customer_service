from app.domains.customer_service.services.shopify_order_context import (
    ShopifyOrderContextBuilder,
)
from app.domains.customer_service.services.shopify_workflow_decisions import (
    ShopifySupportWorkflowDecisionService,
)


def _context(order):
    return ShopifyOrderContextBuilder().build(order)


def test_shipping_status_ready_when_tracking_exists():
    decision = ShopifySupportWorkflowDecisionService().shipping_status(
        _context(
            {
                "id": "1001",
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
                "tracking_number": "TRACK123",
                "tracking_url": "https://carrier.test/TRACK123",
            }
        )
    )

    assert decision["action"] == "shipping_status"
    assert decision["status"] == "ready"
    assert decision["requires_approval"] is False
    assert decision["tracking"]["tracking_number"] == "TRACK123"


def test_refund_requires_approval_for_paid_order_and_blocks_unpaid_order():
    service = ShopifySupportWorkflowDecisionService()

    paid = service.refund(
        _context({"id": "1001", "financial_status": "paid"}),
        reason="customer requested refund",
    )
    assert paid["status"] == "needs_approval"
    assert paid["requires_approval"] is True

    unpaid = service.refund(
        _context({"id": "1002", "financial_status": "pending"}),
    )
    assert unpaid["status"] == "blocked"
    assert unpaid["requires_approval"] is False


def test_cancel_blocks_fulfilled_order_and_requires_approval_before_fulfillment():
    service = ShopifySupportWorkflowDecisionService()

    fulfilled = service.cancel(
        _context({"id": "1001", "fulfillment_status": "fulfilled"}),
    )
    assert fulfilled["status"] == "blocked"

    unfulfilled = service.cancel(
        _context({"id": "1002", "fulfillment_status": "unfulfilled"}),
    )
    assert unfulfilled["status"] == "needs_approval"
    assert unfulfilled["requires_approval"] is True


def test_change_address_requires_address_and_blocks_fulfilled_order():
    service = ShopifySupportWorkflowDecisionService()

    missing_address = service.change_address(
        _context({"id": "1001", "fulfillment_status": "unfulfilled"}),
    )
    assert missing_address["status"] == "needs_information"

    prepared = service.change_address(
        _context({"id": "1002", "fulfillment_status": "unfulfilled"}),
        new_address={"city": "Berlin"},
    )
    assert prepared["status"] == "needs_approval"
    assert prepared["new_address"] == {"city": "Berlin"}

    fulfilled = service.change_address(
        _context({"id": "1003", "fulfillment_status": "fulfilled"}),
        new_address={"city": "Berlin"},
    )
    assert fulfilled["status"] == "blocked"


def test_damaged_item_always_prepares_review_case():
    decision = ShopifySupportWorkflowDecisionService().damaged_item(
        _context({"id": "1001", "financial_status": "paid"}),
        reason="broken",
        note="customer sent photo",
    )

    assert decision["status"] == "needs_approval"
    assert "replacement" in decision["eligible_actions"]
    assert "refund" in decision["eligible_actions"]
