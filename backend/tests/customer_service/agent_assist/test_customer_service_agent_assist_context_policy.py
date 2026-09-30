from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "agent-assist-context-policy@example.com"


@pytest.mark.asyncio
async def test_agent_assist_uses_recent_context_policy(monkeypatch):
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
                        "name": "Agent Assist Context",
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
                        "subject": "Context limit",
                    },
                )
            ).json()

            for body in [
                "Very old refund context that should not dominate the prompt.",
                "Current message one.",
                "Current message two.",
            ]:
                response = await client.post(
                    f"/customer-service/conversations/{conversation['id']}/messages",
                    json={"sender_type": "customer", "body": body},
                )
                assert response.status_code == 200

            suggestion = await client.post(
                f"/customer-service/conversations/{conversation['id']}/agent-assist/reply-suggestion"
            )

            assert suggestion.status_code == 200
            data = suggestion.json()
            assert data["conversation_id"] == conversation["id"]
            assert data["source"] == "workflow_runtime"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
