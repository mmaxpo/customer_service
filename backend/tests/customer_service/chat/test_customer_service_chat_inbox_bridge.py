from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "chat-inbox@example.com"


@pytest.mark.asyncio
async def test_public_chat_session_and_message_appear_in_inbox():
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

            session = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )
            assert session.status_code == 200
            session_body = session.json()
            assert session_body["conversation_id"]
            assert session_body["ticket_id"]

            message = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions/{session_body['id']}/messages",
                json={
                    "content": "Hello, I need help from chat",
                },
            )
            assert message.status_code == 200
            message_body = message.json()
            assert message_body["conversation_id"] == session_body["conversation_id"]
            assert message_body["inbox_message_id"]

            inbox = await client.get("/customer-service/inbox/")
            assert inbox.status_code == 200

            rows = inbox.json()
            assert any(
                row["conversation_id"] == session_body["conversation_id"]
                and row["latest_message"] == "Hello, I need help from chat"
                for row in rows
            )

            detail = await client.get(
                f"/customer-service/conversations/{session_body['conversation_id']}"
            )
            assert detail.status_code == 200

            messages = detail.json()["messages"]
            assert any(
                msg["body"] == "Hello, I need help from chat"
                and msg["meta"]["source"] == "customer_chat"
                for msg in messages
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
