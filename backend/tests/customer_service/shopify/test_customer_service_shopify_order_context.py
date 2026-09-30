from app.domains.customer_service.services.shopify_order_context import (
    ShopifyOrderContextBuilder,
)


def test_shopify_order_context_normalizes_fulfilled_paid_order():
    context = ShopifyOrderContextBuilder().build(
        {
            "id": "1001",
            "name": "#1001",
            "email": "customer@example.com",
            "financial_status": "paid",
            "fulfillment_status": "fulfilled",
            "total_price": "99.00",
            "currency": "EUR",
            "shipping_address": {"city": "Berlin"},
            "fulfillments": [
                {
                    "tracking_number": "TRACK123",
                    "tracking_url": "https://carrier.test/TRACK123",
                    "tracking_company": "DHL",
                }
            ],
        }
    )

    assert context.order_id == "1001"
    assert context.order_name == "#1001"
    assert context.customer_email == "customer@example.com"
    assert context.is_paid is True
    assert context.is_fulfilled is True
    assert context.can_refund is True
    assert context.can_cancel is False
    assert context.can_change_address is False
    assert context.tracking.tracking_number == "TRACK123"
    assert context.tracking.tracking_url == "https://carrier.test/TRACK123"
    assert context.tracking.carrier == "DHL"


def test_shopify_order_context_allows_cancel_and_address_change_before_fulfillment():
    context = ShopifyOrderContextBuilder().build(
        {
            "id": "1002",
            "name": "#1002",
            "financial_status": "paid",
            "fulfillment_status": "unfulfilled",
        }
    )

    assert context.can_refund is True
    assert context.can_cancel is True
    assert context.can_change_address is True


def test_shopify_order_context_defaults_missing_fulfillment_to_unfulfilled():
    context = ShopifyOrderContextBuilder().build(
        {
            "id": "1001",
            "financial_status": "paid",
            "fulfillment_status": None,
        }
    )

    assert context.fulfillment_status == "unfulfilled"
    assert context.is_fulfilled is False
    assert context.can_cancel is True
