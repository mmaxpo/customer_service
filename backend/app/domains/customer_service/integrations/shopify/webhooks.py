from app.platform.webhooks.providers.base import NormalizedWebhookEvent


class ShopifyWebhookAdapter:
    source = "shopify"

    EVENT_MAP = {
        "orders/create": "orders.created",
        "orders/updated": "orders.updated",
        "orders/cancelled": "orders.cancelled",
        "fulfillments/create": "fulfillments.created",
        "refunds/create": "refunds.created",
    }

    def normalize(self, *, event_type: str, payload: dict, headers: dict):
        normalized_event_type = self.EVENT_MAP.get(event_type, event_type)

        order_id = payload.get("id") or payload.get("order_id")
        order_name = payload.get("name")
        email = payload.get("email")

        normalized = {
            "order_id": str(order_id) if order_id is not None else None,
            "order_name": order_name,
            "customer_email": email,
            "financial_status": payload.get("financial_status"),
            "fulfillment_status": payload.get("fulfillment_status"),
            "total_price": payload.get("total_price"),
            "currency": payload.get("currency"),
            "raw_event_type": event_type,
        }

        return NormalizedWebhookEvent(
            source="shopify",
            event_type=normalized_event_type,
            external_id=str(order_id) if order_id is not None else None,
            normalized_payload=normalized,
            raw_payload=payload,
            headers=headers,
        )
