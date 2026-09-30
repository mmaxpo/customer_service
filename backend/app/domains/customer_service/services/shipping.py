from fastapi import HTTPException

from app.integrations.gateway import default_gateway

from app.domains.customer_service.providers.shipping import (
    FakeShippingProvider,
    ShippingProvider,
)
from app.domains.customer_service.repositories.shipping import ShippingRepository


class ShippingService:
    def __init__(
        self,
        db,
        provider_impl: ShippingProvider | None = None,
    ):
        self.db = db
        self.repo = ShippingRepository(db)
        self.provider_impl = provider_impl or FakeShippingProvider()

    async def track(
        self,
        *,
        user_id,
        tracking_number: str,
        provider: str = "generic",
    ):
        tracking_number = self._normalize_tracking_number(tracking_number)
        provider = self._normalize_provider(provider)

        cached = await self.repo.find_cached_tracking(
            user_id=user_id,
            provider=provider,
            tracking_number=tracking_number,
        )

        if cached is not None:
            return cached

        result = await default_gateway.call(
            provider=f"shipping.{provider}",
            operation="track",
            func=lambda: self.provider_impl.track(
                provider=provider,
                tracking_number=tracking_number,
            ),
        )

        if result is None:
            raise HTTPException(status_code=404, detail="Tracking number not found")

        return await self.repo.cache_tracking(
            user_id=user_id,
            provider=provider,
            tracking_number=tracking_number,
            status=result.get("status"),
            payload=result,
        )

    def _normalize_tracking_number(self, tracking_number: str) -> str:
        value = (tracking_number or "").strip()

        if not value:
            raise HTTPException(status_code=422, detail="tracking_number is required")

        return value

    def _normalize_provider(self, provider: str) -> str:
        value = (provider or "generic").strip().lower()

        if not value:
            return "generic"

        return value
