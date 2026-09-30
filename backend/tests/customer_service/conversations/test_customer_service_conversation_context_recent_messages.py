from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "context-recent-messages@example.com"


@pytest.mark.asyncio
async def test_conversation_context_returns_bounded_recent_messages(monkeypatch):
    monkeypatch.setenv("TAJERAN_CS_AI_RECENT_MESSAGE_LIMIT", "2")

    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Context Recent",
                        "email": f"{uuid4()}@example.com",
                    },
                )
            ).json()

            conversation = (
                await client.post(
                    "/customer-service/conversations/",
                    json={
                        "customer_id": customer["id"],
                        "channel": "email",
                        "subject": "Context recent messages",
                    },
                )
            ).json()

            for index in range(4):
                response = await client.post(
                    f"/customer-service/conversations/{conversation['id']}/messages",
                    json={
                        "sender_type": "customer",
                        "body": f"context-message-{index}",
                    },
                )
                assert response.status_code == 200

            response = await client.get(
                f"/customer-service/conversations/{conversation['id']}/context"
            )

            assert response.status_code == 200
            data = response.json()

            assert "messages" not in data["conversation"]
            assert [m["body"] for m in data["recent_messages"]] == [
                "context-message-2",
                "context-message-3",
            ]

    finally:
        app.dependency_overrides.pop(get_current_user, None)
