from app.platform.webhooks.providers.base import NormalizedWebhookEvent


class GenericWebhookAdapter:
    def __init__(self, source: str = "generic"):
        self.source = (source or "generic").strip().lower()

    def normalize(self, *, event_type: str, payload: dict, headers: dict):
        return NormalizedWebhookEvent(
            source=self.source,
            event_type=event_type,
            external_id=str(payload.get("id"))
            if payload.get("id") is not None
            else None,
            normalized_payload=payload,
            raw_payload=payload,
            headers=headers,
        )
