import base64
import hashlib
import hmac as hmac_lib
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.session import SessionLocal
from app.models.models import User
from app.domains.customer_service.models import (
    CustomerServiceShopifyOrderCache,
    ShopifyWebhookReceipt,
)
from sqlalchemy import select


async def _mark_verified(email: str) -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        assert user is not None
        user.email_verified_at = datetime.now(timezone.utc)
        await db.commit()


def _hmac(params: dict[str, str], secret: str = "dev-shopify-api-secret") -> str:
    message = "&".join(f"{key}={params[key]}" for key in sorted(params))

    return hmac_lib.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _webhook_hmac(body: bytes, secret: str = "dev-shopify-api-secret") -> str:
    return base64.b64encode(
        hmac_lib.new(secret.encode(), body, hashlib.sha256).digest()
    ).decode()


@pytest.mark.asyncio
async def test_shopify_install_returns_normalized_install_url():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        email = f"shopify-install-{uuid4()}@example.com"
        password = f"Shopify-{uuid4()}"
        assert (
            await client.post(
                "/auth/signup",
                json={
                    "email": email,
                    "password": password,
                    "terms_accepted": True,
                    "terms_version": "v1",
                    "privacy_accepted": True,
                    "privacy_version": "v1",
                },
            )
            ).status_code == 201
        await _mark_verified(email)
        assert (
            await client.post(
                "/auth/login",
                json={
                    "email": email,
                    "password": password,
                    "terms_accepted": True,
                    "terms_version": "v1",
                    "privacy_accepted": True,
                    "privacy_version": "v1",
                },
            )
        ).status_code == 200
        response = await client.post(
            "/customer-service/shopify/install",
            json={"shop_domain": "Example"},
        )

        assert response.status_code == 200

        data = response.json()

        assert data["shop_domain"] == "example.myshopify.com"
        assert len(data["state"]) >= 48
        assert ":" not in data["state"]
        assert (
            "https://example.myshopify.com/admin/oauth/authorize?"
            in data["install_url"]
        )
        assert "client_id=dev-shopify-api-key" in data["install_url"]
        assert "read_orders" in data["install_url"]


@pytest.mark.asyncio
async def test_shopify_oauth_callback_validates_hmac():
    params = {
        "shop": "example.myshopify.com",
        "code": "temporary-code",
        "state": "state-123",
    }
    valid_hmac = _hmac(params)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        valid = await client.get(
            "/customer-service/shopify/oauth/callback",
            params={**params, "hmac": valid_hmac},
        )

        assert valid.status_code == 400
        assert "state" in valid.json()["detail"].lower()

        invalid = await client.get(
            "/customer-service/shopify/oauth/callback",
            params={**params, "hmac": "invalid"},
        )

        assert invalid.status_code == 401


@pytest.mark.asyncio
async def test_shopify_oauth_callback_connects_state_user_and_provisions_widget(
    monkeypatch,
):
    from urllib.parse import urlencode
    from uuid import uuid4

    from httpx import ASGITransport, AsyncClient

    from app.domains.customer_service.integrations.shopify.oauth import (
        ShopifyOAuthService,
    )
    from app.main import app

    shop = "example.myshopify.com"

    async def fake_exchange(self, *, shop_domain, code):
        return {
            "access_token": "oauth-token-for-state-user",
            "scope": ",".join(self.scopes),
        }

    async def fake_register(self, **_kwargs):
        return None

    monkeypatch.setattr(
        ShopifyOAuthService,
        "exchange_code_for_access_token",
        fake_exchange,
    )
    monkeypatch.setattr(
        ShopifyOAuthService,
        "register_compliance_webhooks",
        fake_register,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        email = f"shopify-callback-{uuid4()}@example.com"
        password = f"Shopify-{uuid4()}"
        assert (
                await client.post(
                    "/auth/signup",
                    json={
                        "email": email,
                        "password": password,
                        "terms_accepted": True,
                        "terms_version": "v1",
                        "privacy_accepted": True,
                        "privacy_version": "v1",
                    },
                )
            ).status_code == 201
        await _mark_verified(email)
        assert (
            await client.post(
                "/auth/login",
                json={"email": email, "password": password},
            )
        ).status_code == 200
        install = await client.post(
            "/customer-service/shopify/install",
            json={"shop_domain": shop},
        )
        assert install.status_code == 200
        params = {
            "shop": shop,
            "code": "test-code",
            "state": install.json()["state"],
            "timestamp": "1234567890",
        }
        params["hmac"] = _hmac(params)
        response = await client.get(
            f"/customer-service/shopify/oauth/callback?{urlencode(params)}"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["shop_domain"] == shop
    assert data["valid"] is True
    assert data["connected"] is True
    assert data["connection_id"] is not None

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        replay = await client.get(
            f"/customer-service/shopify/oauth/callback?{urlencode(params)}"
        )
    assert replay.status_code == 400


@pytest.mark.asyncio
async def test_shopify_uninstall_webhook_is_verified_and_idempotent():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        email = f"shopify-webhook-{uuid4()}@example.com"
        password = f"Shopify-{uuid4()}"
        await client.post(
            "/auth/signup",
            json={
                "email": email,
                "password": password,
                "terms_accepted": True,
                "terms_version": "v1",
                "privacy_accepted": True,
                "privacy_version": "v1",
            },
        )
        await _mark_verified(email)
        await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        connected = await client.post(
            "/customer-service/shopify/connect",
            json={
                "shop_domain": "webhook-store.myshopify.com",
                "access_token": "secret-token",
            },
        )
        assert connected.status_code == 200

        body = json.dumps(
            {"id": 123, "domain": "webhook-store.myshopify.com"},
            separators=(",", ":"),
        ).encode()
        headers = {
            "content-type": "application/json",
            "x-shopify-topic": "app/uninstalled",
            "x-shopify-shop-domain": "webhook-store.myshopify.com",
            "x-shopify-webhook-id": str(uuid4()),
            "x-shopify-hmac-sha256": _webhook_hmac(body),
        }
        invalid = await client.post(
            "/customer-service/shopify/webhooks",
            content=body,
            headers={**headers, "x-shopify-hmac-sha256": "invalid"},
        )
        assert invalid.status_code == 401

        accepted = await client.post(
            "/customer-service/shopify/webhooks",
            content=body,
            headers=headers,
        )
        assert accepted.status_code == 202
        assert accepted.json()["status"] == "processed"

        duplicate = await client.post(
            "/customer-service/shopify/webhooks",
            content=body,
            headers=headers,
        )
        assert duplicate.status_code == 202
        assert duplicate.json()["status"] == "duplicate"

        connection = await client.get("/customer-service/shopify/connection")
        assert connection.status_code == 200
        assert connection.json() is None


@pytest.mark.asyncio
async def test_shopify_data_request_webhook_is_verified_and_queued_for_export():
    """Mandatory privacy requests are acknowledged and durably recorded."""
    body = json.dumps(
        {
            "shop_id": 123,
            "shop_domain": "privacy-store.myshopify.com",
            "orders_requested": [456],
            "customer": {"id": 789, "email": "customer@example.com"},
            "data_request": {"id": 999},
        },
        separators=(",", ":"),
    ).encode()
    webhook_id = str(uuid4())
    headers = {
        "content-type": "application/json",
        "x-shopify-topic": "customers/data_request",
        "x-shopify-shop-domain": "privacy-store.myshopify.com",
        "x-shopify-webhook-id": webhook_id,
        "x-shopify-hmac-sha256": _webhook_hmac(body),
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/customer-service/shopify/webhooks",
            content=body,
            headers=headers,
        )

    assert response.status_code == 202
    assert response.json() == {"status": "pending_export"}
    async with SessionLocal() as db:
        receipt = await db.scalar(
            select(ShopifyWebhookReceipt).where(
                ShopifyWebhookReceipt.webhook_id == webhook_id
            )
        )
        assert receipt is not None
        assert receipt.status == "pending_export"


@pytest.mark.asyncio
async def test_shopify_order_webhook_updates_cache_and_deduplicates():
    shop = "commerce-webhook-store.myshopify.com"
    email = f"shopify-commerce-{uuid4()}@example.com"
    password = f"Shopify-{uuid4()}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (
            await client.post(
                "/auth/signup",
                json={
                    "email": email,
                    "password": password,
                    "terms_accepted": True,
                    "terms_version": "v1",
                    "privacy_accepted": True,
                    "privacy_version": "v1",
                },
            )
        ).status_code == 201
        await _mark_verified(email)
        assert (await client.post("/auth/login", json={"email": email, "password": password})).status_code == 200
        assert (
            await client.post(
                "/customer-service/shopify/connect",
                json={"shop_domain": shop, "access_token": "dev-token"},
            )
        ).status_code == 200

        body = json.dumps(
            {"id": 987654, "name": "#1009", "email": email, "financial_status": "paid"},
            separators=(",", ":"),
        ).encode()
        headers = {
            "content-type": "application/json",
            "x-shopify-topic": "orders/updated",
            "x-shopify-shop-domain": shop,
            "x-shopify-webhook-id": str(uuid4()),
            "x-shopify-hmac-sha256": _webhook_hmac(body),
        }
        accepted = await client.post("/customer-service/shopify/webhooks", content=body, headers=headers)
        assert accepted.status_code == 202
        assert accepted.json() == {"status": "processed"}
        duplicate = await client.post("/customer-service/shopify/webhooks", content=body, headers=headers)
        assert duplicate.status_code == 202
        assert duplicate.json() == {"status": "duplicate"}

    async with SessionLocal() as db:
        cached = await db.scalar(
            select(CustomerServiceShopifyOrderCache).where(
                CustomerServiceShopifyOrderCache.shop_domain == shop,
                CustomerServiceShopifyOrderCache.order_id == "987654",
            )
        )
        assert cached is not None
        assert cached.order_name == "#1009"
