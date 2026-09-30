from __future__ import annotations

from app.domains.customer_service.integrations.omnichannel.base import (
    OmnichannelProviderAdapter,
)


class OmnichannelProviderRegistry:
    def __init__(self):
        self._adapters: dict[str, OmnichannelProviderAdapter] = {}

    def register(self, adapter: OmnichannelProviderAdapter) -> None:
        self._adapters[adapter.channel] = adapter

    def list(self):
        return list(self._adapters.values())

    def get(self, channel: str) -> OmnichannelProviderAdapter:
        adapter = self._adapters.get(channel)
        if adapter is None:
            adapter = self._adapters.get("generic")
        if adapter is None:
            raise LookupError(
                f"No omnichannel provider adapter registered for channel={channel!r}"
            )
        return adapter

    def list_channels(self) -> list[str]:
        return sorted(self._adapters)


_provider_registry = OmnichannelProviderRegistry()


def get_omnichannel_provider_registry() -> OmnichannelProviderRegistry:
    return _provider_registry
