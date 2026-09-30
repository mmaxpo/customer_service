from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "ai-context-policy@example.com"


@pytest.mark.asyncio
async def test_conversation_intelligence_uses_recent_bounded_context(monkeypatch):
    monkeypatch.setenv("TAJERAN_CS_AI_INTELLIGENCE_SCAN_MESSAGE_LIMIT", "2")

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
                        "name": "Context Policy Customer",
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
                        "subject": "Context policy",
                    },
                )
            ).json()

            for body in [
                "I want a refund for an old issue.",
                "Actually I have a tracking question now.",
                "Where is my order tracking number?",
            ]:
                response = await client.post(
                    f"/customer-service/conversations/{conversation['id']}/messages",
                    json={"sender_type": "customer", "body": body},
                )
                assert response.status_code == 200

            analyze = await client.post(
                f"/customer-service/conversations/{conversation['id']}/intelligence/analyze",
                json={},
            )

            assert analyze.status_code == 200
            data = analyze.json()

            assert data["intent"] == "tracking_request"
            assert "Conversation contains 3 message(s)." in data["summary"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)
