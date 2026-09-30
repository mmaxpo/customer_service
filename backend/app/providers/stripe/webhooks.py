from app.platform.webhooks.providers.base import NormalizedWebhookEvent


class StripeWebhookAdapter:
    source = "stripe"

    def normalize(self, *, event_type: str, payload: dict, headers: dict):
        data = payload.get("data") or {}
        obj = data.get("object") or {}

        external_id = obj.get("id") or payload.get("id")

        normalized = {
            "stripe_event_id": payload.get("id"),
            "object_id": obj.get("id"),
            "object_type": obj.get("object"),
            "amount": obj.get("amount"),
            "currency": obj.get("currency"),
            "status": obj.get("status"),
            "customer": obj.get("customer"),
            "raw_event_type": event_type,
        }

        return NormalizedWebhookEvent(
            source="stripe",
            event_type=event_type,
            external_id=str(external_id) if external_id is not None else None,
            normalized_payload=normalized,
            raw_payload=payload,
            headers=headers,
            provider_event_id=(
                str(payload["id"]) if payload.get("id") is not None else None
            ),
        )
