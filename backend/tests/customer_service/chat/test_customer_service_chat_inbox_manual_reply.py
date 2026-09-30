from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "chat-manual-reply@example.com"


@pytest.mark.asyncio
async def test_inbox_agent_reply_is_visible_in_public_chat_widget_messages():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings = await client.get("/customer-service/chat/widget/settings")
            assert settings.status_code == 200
            public_key = settings.json()["public_key"]

            session_response = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )
            assert session_response.status_code == 200
            session = session_response.json()

            customer_message = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions/{session['id']}/messages",
                json={"content": "Hi, I need help from a human"},
            )
            assert customer_message.status_code == 200

            agent_reply = await client.post(
                f"/customer-service/conversations/{session['conversation_id']}/messages",
                json={
                    "sender_type": "agent",
                    "body": "Hi, this is support. I can help you.",
                },
            )
            assert agent_reply.status_code == 200

            chat_messages = await client.get(
                f"/customer-service/chat/public/{public_key}/sessions/{session['id']}/messages"
            )
            assert chat_messages.status_code == 200

            messages = chat_messages.json()
            assert any(
                msg["role"] == "customer"
                and msg["content"] == "Hi, I need help from a human"
                for msg in messages
            )
            assert any(
                msg["role"] == "assistant"
                and msg["content"] == "Hi, this is support. I can help you."
                for msg in messages
            )

            detail = await client.get(
                f"/customer-service/conversations/{session['conversation_id']}"
            )
            assert detail.status_code == 200

            assert any(
                msg["sender_type"] == "agent"
                and msg["body"] == "Hi, this is support. I can help you."
                for msg in detail.json()["messages"]
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
