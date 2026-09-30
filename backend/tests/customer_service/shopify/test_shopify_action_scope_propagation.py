from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.domains.customer_service.providers.shopify import (
    FakeShopifyProvider,
)
from app.domains.customer_service.services.shopify import (
    ShopifyService,
)


class ScopeCapturingProvider(FakeShopifyProvider):
    def __init__(self):
        self.refund_scopes = []
        self.reship_scopes = []
        self.address_calls = []

    async def refund_order(self, **kwargs):
        self.refund_scopes.append(kwargs.get("scope"))
        return await super().refund_order(**kwargs)

    async def reship_order(self, **kwargs):
        self.reship_scopes.append(kwargs.get("scope"))
        return await super().reship_order(**kwargs)

    async def change_order_address(self, **kwargs):
        self.address_calls.append(
            {
                "new_address": kwargs.get("new_address"),
                "note": kwargs.get("note"),
            }
        )
        return await super().change_order_address(**kwargs)


@pytest.mark.asyncio
async def test_refund_scope_reaches_provider_and_idempotent_result():
    user_id = uuid4()
    provider = ScopeCapturingProvider()
    scope = {
        "line_items": [
            {
                "line_item_id": "101",
                "quantity": 1,
                "amount": None,
            }
        ],
        "replacement_line_item_id": None,
        "replacement_quantity": None,
        "new_address": None,
    }

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
            scope=scope,
            idempotency_key="scoped-refund-101",
        )
        second = await service.perform_order_action(
            user_id=user_id,
            action="refund",
            order_ref="1001",
            reason="Damaged item",
            scope=scope,
            idempotency_key="scoped-refund-101",
        )

        assert provider.refund_scopes == [scope]
        assert first == second
        assert first["scope"] == scope
        assert first["payload"]["scope"] == scope


@pytest.mark.asyncio
async def test_replacement_scope_reaches_reship_provider():
    user_id = uuid4()
    provider = ScopeCapturingProvider()
    scope = {
        "line_items": [],
        "replacement_line_item_id": "102",
        "replacement_quantity": 1,
        "new_address": {
            "formatted": "123 Main Street, Miami, FL 33101"
        },
    }

    async with SessionLocal() as db:
        service = ShopifyService(db, provider=provider)

        await service.connect(
            user_id=user_id,
            shop_domain="example.myshopify.com",
            access_token="test-token",
        )

        result = await service.perform_order_action(
            user_id=user_id,
            action="reship",
            order_ref="1001",
            reason="Damaged item",
            note="Approved replacement",
            scope=scope,
            idempotency_key="scoped-reship-102",
        )

        assert provider.reship_scopes == [scope]
        assert result["status"] == "prepared"
        assert result["scope"] == scope


@pytest.mark.asyncio
async def test_address_action_uses_change_order_address_contract():
    user_id = uuid4()
    provider = ScopeCapturingProvider()
    address = {
        "address1": "123 Main Street",
        "city": "Miami",
        "province": "FL",
        "zip": "33101",
        "country": "US",
    }

    async with SessionLocal() as db:
        service = ShopifyService(db, provider=provider)

        await service.connect(
            user_id=user_id,
            shop_domain="example.myshopify.com",
            access_token="test-token",
        )

        result = await service.perform_order_action(
            user_id=user_id,
            action="update_shipping_address",
            order_ref="1001",
            new_address=address,
            note="Approved replacement address",
            idempotency_key="address-contract-1001",
        )

        assert provider.address_calls == [
            {
                "new_address": address,
                "note": "Approved replacement address",
            }
        ]
        # Fake order 1001 is fulfilled, so the fake provider safely blocks it.
        assert result["status"] == "blocked"
