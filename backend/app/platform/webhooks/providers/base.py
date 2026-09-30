from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class NormalizedWebhookEvent:
    source: str
    event_type: str
    external_id: str | None
    normalized_payload: dict
    raw_payload: dict
    headers: dict
    provider_event_id: str | None = None


class WebhookProviderAdapter(Protocol):
    source: str

    def normalize(
        self,
        *,
        event_type: str,
        payload: dict,
        headers: dict,
    ) -> NormalizedWebhookEvent: ...
