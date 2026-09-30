from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "agent-assist@example.com"


@pytest.mark.asyncio
async def test_agent_assist_reply_suggestion_uses_workflow_runtime():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            customer_res = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Agent Assist Customer",
                    "email": f"{uuid4()}@example.com",
                    "phone": "+49123456789",
                },
            )
            assert customer_res.status_code == 200
            customer = customer_res.json()

            conversation_res = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": customer["id"],
                    "channel": "email",
                    "subject": "Damaged item",
                },
            )
            assert conversation_res.status_code == 200
            conversation = conversation_res.json()

            message_res = await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "My item arrived damaged and broken.",
                },
            )
            assert message_res.status_code == 200

            assist_res = await client.post(
                f"/customer-service/conversations/{conversation['id']}/agent-assist/reply-suggestion"
            )
            assert assist_res.status_code == 200

            data = assist_res.json()

            assert data["source"] == "workflow_runtime"
            assert data["intent"] == "damaged_product"
            assert data["confidence"] == 0.9
            assert data["workflow_run_id"]
            assert data["suggestion"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)
