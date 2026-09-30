from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "test@example.com"


@pytest.mark.asyncio
async def test_customer_service_customer_conversation_message_inbox_flow():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        customer_response = await client.post(
            "/customer-service/customers/",
            json={
                "name": "Test Customer",
                "email": "customer@example.com",
                "phone": "+491111111",
            },
        )

        assert customer_response.status_code == 200
        customer = customer_response.json()

        conversation_response = await client.post(
            "/customer-service/conversations/",
            json={
                "customer_id": customer["id"],
                "channel": "email",
                "subject": "Test support issue",
            },
        )

        assert conversation_response.status_code == 200
        conversation = conversation_response.json()

        message_response = await client.post(
            f"/customer-service/conversations/{conversation['id']}/messages",
            json={
                "sender_type": "customer",
                "body": "I need help with my order.",
            },
        )

        assert message_response.status_code == 200

        inbox_response = await client.get("/customer-service/inbox/")
        assert inbox_response.status_code == 200

        inbox = inbox_response.json()

        assert len(inbox) >= 1
        assert inbox[0]["customer_name"] == "Test Customer"
        assert inbox[0]["latest_message"] == "I need help with my order."
        assert inbox[0]["ticket"] is not None
        assert inbox[0]["ticket"]["status"] == "open"

    app.dependency_overrides.pop(get_current_user, None)
