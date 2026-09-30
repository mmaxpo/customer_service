from __future__ import annotations

from typing import Protocol


class ShippingProvider(Protocol):
    async def track(
        self,
        *,
        provider: str,
        tracking_number: str,
    ) -> dict | None: ...


class FakeShippingProvider:
    async def track(
        self,
        *,
        provider: str,
        tracking_number: str,
    ) -> dict | None:
        return {
            "provider": provider,
            "tracking_number": tracking_number,
            "status": "in_transit",
            "estimated_delivery": "2026-05-29",
            "last_event": {
                "description": "Package is in transit",
                "location": "Frankfurt, DE",
            },
        }
