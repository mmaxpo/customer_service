from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "chat-widget@example.com"


@pytest.mark.asyncio
async def test_chat_widget_settings_can_be_created_and_updated():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/customer-service/chat/widget/settings")
            assert response.status_code == 200

            data = response.json()
            assert data["public_key"].startswith("cw_")
            assert data["enabled"] is True
            assert data["title"] == "Chat with us"

            response = await client.put(
                "/customer-service/chat/widget/settings",
                json={
                    "title": "Support Chat",
                    "welcome_message": "Welcome to our store!",
                    "brand_color": "#111827",
                    "assistant_name": "Store AI",
                    "auto_answer_enabled": False,
                },
            )
            assert response.status_code == 200

            data = response.json()
            assert data["title"] == "Support Chat"
            assert data["welcome_message"] == "Welcome to our store!"
            assert data["brand_color"] == "#111827"
            assert data["assistant_name"] == "Store AI"
            assert data["auto_answer_enabled"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_public_chat_widget_settings_and_session_flow():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/customer-service/chat/widget/settings")
            assert response.status_code == 200
            public_key = response.json()["public_key"]

            response = await client.get(
                f"/customer-service/chat/public/{public_key}/settings"
            )
            assert response.status_code == 200
            assert response.json()["public_key"] == public_key

            response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": "visitor_123",
                    "channel": "website",
                },
            )
            assert response.status_code == 200
            session_id = response.json()["id"]

            response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions/{session_id}/messages",
                json={
                    "content": "Where is my order?",
                },
            )
            assert response.status_code == 200
            assert response.json()["role"] == "customer"

            response = await client.get(
                f"/customer-service/chat/public/{public_key}/sessions/{session_id}/messages"
            )
            assert response.status_code == 200

            messages = response.json()
            assert len(messages) == 1
            assert messages[0]["content"] == "Where is my order?"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
