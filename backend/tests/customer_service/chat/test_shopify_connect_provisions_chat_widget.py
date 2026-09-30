from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "shopify-widget@example.com"


@pytest.mark.asyncio
async def test_shopify_connect_provisions_chat_widget_settings():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            connected = await client.post(
                "/customer-service/shopify/connect",
                json={
                    "shop_domain": "tajeran-support-dev.myshopify.com",
                    "access_token": "test-token",
                },
            )

            assert connected.status_code == 200

            settings = await client.get("/customer-service/chat/widget/settings")

            assert settings.status_code == 200
            body = settings.json()
            assert body["enabled"] is True
            assert body["public_key"].startswith("cw_")

    finally:
        app.dependency_overrides.pop(get_current_user, None)
