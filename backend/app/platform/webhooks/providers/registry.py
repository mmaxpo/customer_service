from __future__ import annotations

from app.platform.webhooks.providers.base import WebhookProviderAdapter
from app.platform.webhooks.providers.generic import GenericWebhookAdapter


class WebhookProviderRegistry:
    def __init__(self):
        self._adapters: dict[
            str,
            WebhookProviderAdapter,
        ] = {}

    def register(
        self,
        source: str,
        adapter: WebhookProviderAdapter,
    ) -> None:
        normalized = (source or "").strip().lower()

        if not normalized:
            raise ValueError("webhook provider source is required")

        self._adapters[normalized] = adapter

    def get(
        self,
        source: str,
    ) -> WebhookProviderAdapter:
        normalized = (source or "generic").strip().lower()

        adapter = self._adapters.get(normalized)

        if adapter is not None:
            return adapter

        return GenericWebhookAdapter(source=normalized)


def build_core_webhook_provider_registry() -> WebhookProviderRegistry:
    registry = WebhookProviderRegistry()

    generic = GenericWebhookAdapter()

    registry.register(
        "generic",
        generic,
    )

    registry.register(
        "custom",
        GenericWebhookAdapter(source="custom"),
    )

    return registry


# Generic compatibility object only.
# Product/provider composition belongs to app.platform.composition.
default_webhook_provider_registry = build_core_webhook_provider_registry()


__all__ = [
    "WebhookProviderRegistry",
    "build_core_webhook_provider_registry",
    "default_webhook_provider_registry",
]
