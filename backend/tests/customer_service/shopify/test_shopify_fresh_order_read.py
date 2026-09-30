from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.domains.customer_service.providers.shopify import (
    FakeShopifyProvider,
)
from app.domains.customer_service.services.shopify import (
    ShopifyService,
)


class CountingFreshOrderProvider(
    FakeShopifyProvider
):
    def __init__(self):
        self.calls = 0

    async def get_order(
        self,
        *,
        shop_domain,
        access_token,
        order_ref,
    ):
        self.calls += 1

        return {
            "id": order_ref,
            "name": order_ref,
            "cancelled_at": (
                "2026-07-18T12:00:00Z"
            ),
            "financial_status": "voided",
            "fulfillment_status": None,
        }


@pytest.mark.asyncio
async def test_get_order_fresh_bypasses_cached_order():
    user_id = uuid4()
    provider = CountingFreshOrderProvider()

    async with SessionLocal() as db:
        service = ShopifyService(
            db,
            provider=provider,
        )

        await service.connect(
            user_id=user_id,
            shop_domain=(
                "fresh-read.myshopify.com"
            ),
            access_token="test-token",
        )

        first = await service.get_order(
            user_id=user_id,
            order_ref="#2001",
        )
        second = await service.get_order(
            user_id=user_id,
            order_ref="#2001",
        )

        assert first["order_id"] == "#2001"
        assert second["order_id"] == "#2001"
        assert provider.calls == 1

        fresh = await service.get_order_fresh(
            user_id=user_id,
            order_ref="#2001",
        )

        assert (
            fresh["cancelled_at"]
            == "2026-07-18T12:00:00Z"
        )
        assert provider.calls == 2
