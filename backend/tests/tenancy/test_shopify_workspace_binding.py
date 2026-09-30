from __future__ import annotations

from uuid import uuid4

from app.api.products.customer_service.providers import shopify
from app.domains.customer_service.schemas.shopify import ShopifyConnectionCreate
from app.domains.customer_service.security.rbac import CustomerServicePrincipal


async def test_legacy_shopify_connect_routes_the_resolved_workspace_to_the_provider(
    monkeypatch,
):
    captured = {}

    workspace_id = uuid4()
    actor_id = uuid4()

    class FakeShopifyService:
        def __init__(self, db):
            assert db is None

        async def connect(self, **kwargs):
            captured.update(kwargs)
            return kwargs

    monkeypatch.setattr(shopify, "ShopifyService", FakeShopifyService)
    principal = CustomerServicePrincipal(
        user=type("User", (), {"id": actor_id})(),
        workspace_id=workspace_id,
        role="owner",
    )

    await shopify.connect_shopify(
        payload=ShopifyConnectionCreate(
            shop_domain="merchant.myshopify.com",
            access_token="secret",
        ),
        db=None,
        current_user=principal,
    )

    assert captured["user_id"] == workspace_id
    assert captured["workspace_id"] == workspace_id
