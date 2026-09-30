from app.domains.customer_service.integrations.shopify.webhooks import (
    ShopifyWebhookAdapter,
)
from app.providers.stripe.webhooks import StripeWebhookAdapter


def test_shopify_webhook_adapter_normalizes_order_created():
    event = ShopifyWebhookAdapter().normalize(
        event_type="orders/create",
        payload={
            "id": 1001,
            "name": "#1001",
            "email": "customer@example.com",
            "financial_status": "paid",
            "fulfillment_status": "fulfilled",
            "total_price": "99.00",
            "currency": "EUR",
        },
        headers={},
    )

    assert event.source == "shopify"
    assert event.event_type == "orders.created"
    assert event.external_id == "1001"
    assert event.normalized_payload["order_name"] == "#1001"
    assert event.normalized_payload["customer_email"] == "customer@example.com"


def test_stripe_webhook_adapter_normalizes_payment_event():
    event = StripeWebhookAdapter().normalize(
        event_type="payment_intent.succeeded",
        payload={
            "id": "evt_123",
            "data": {
                "object": {
                    "id": "pi_123",
                    "object": "payment_intent",
                    "amount": 5000,
                    "currency": "usd",
                    "status": "succeeded",
                    "customer": "cus_123",
                }
            },
        },
        headers={},
    )

    assert event.source == "stripe"
    assert event.event_type == "payment_intent.succeeded"
    assert event.external_id == "pi_123"
    assert event.normalized_payload["amount"] == 5000
    assert event.normalized_payload["customer"] == "cus_123"


def test_stripe_provider_event_id_is_distinct_from_business_object_id():
    event = StripeWebhookAdapter().normalize(
        event_type="payment_intent.succeeded",
        payload={
            "id": "evt_delivery_123",
            "data": {
                "object": {
                    "id": "pi_business_123",
                    "object": "payment_intent",
                    "amount": 5000,
                    "currency": "usd",
                    "status": "succeeded",
                }
            },
        },
        headers={},
    )

    assert event.external_id == "pi_business_123"
    assert event.provider_event_id == "evt_delivery_123"


def test_custom_webhook_adapter_preserves_custom_source():
    from app.platform.webhooks.providers.registry import (
        build_core_webhook_provider_registry,
    )

    registry = build_core_webhook_provider_registry()

    event = registry.get("custom").normalize(
        event_type="customer.changed",
        payload={
            "id": "custom-1",
            "value": "hello",
        },
        headers={},
    )

    assert event.source == "custom"
    assert event.event_type == "customer.changed"
    assert event.external_id == "custom-1"
    assert event.raw_payload == {
        "id": "custom-1",
        "value": "hello",
    }


def test_unknown_webhook_provider_preserves_configured_source():
    from app.platform.webhooks.providers.registry import (
        build_core_webhook_provider_registry,
    )

    registry = build_core_webhook_provider_registry()

    event = registry.get("acme").normalize(
        event_type="widget.changed",
        payload={
            "id": "acme-1",
            "status": "updated",
        },
        headers={},
    )

    assert event.source == "acme"
    assert event.event_type == "widget.changed"
    assert event.external_id == "acme-1"
    assert event.raw_payload == {
        "id": "acme-1",
        "status": "updated",
    }
