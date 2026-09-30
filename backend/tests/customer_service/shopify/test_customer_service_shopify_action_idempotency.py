from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.domains.customer_service.providers.shopify import FakeShopifyProvider
from app.domains.customer_service.services.shopify import ShopifyService


class CountingShopifyProvider(FakeShopifyProvider):
    def __init__(self):
        self.refund_calls = 0

    async def refund_order(self, **kwargs):
        self.refund_calls += 1
        result = await super().refund_order(**kwargs)
        result["provider_refund_calls"] = self.refund_calls
        return result


@pytest.mark.asyncio
async def test_shopify_refund_repeated_with_same_idempotency_key_executes_once():
    user_id = uuid4()
    provider = CountingShopifyProvider()

    async with SessionLocal() as db:
        service = ShopifyService(db, provider=provider)

        await service.connect(
            user_id=user_id,
            shop_domain="example.myshopify.com",
            access_token="test-token",
        )

        first = await service.perform_order_action(
            user_id=user_id,
            action="refund",
            order_ref="1001",
            reason="Damaged item",
            amount="99.00",
            idempotency_key="shopify-refund-once-key",
        )

        second = await service.perform_order_action(
            user_id=user_id,
            action="refund",
            order_ref="1001",
            reason="Damaged item",
            amount="99.00",
            idempotency_key="shopify-refund-once-key",
        )

        assert provider.refund_calls == 1
        assert second == first
        assert second["idempotency_key"] == "shopify-refund-once-key"
        assert second["payload"]["provider_refund_calls"] == 1
