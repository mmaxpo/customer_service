from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "omnichannel@example.com"


@pytest.mark.asyncio
async def test_omnichannel_inbound_creates_customer_conversation_ticket_and_message():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-business-1",
                    "external_thread_id": "thread-1",
                    "external_message_id": "message-1",
                    "external_customer_id": "customer-1",
                    "customer_name": "Omni Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "customer_phone": "+46700000000",
                    "subject": "WhatsApp support request",
                    "body": "My order arrived damaged and I need help urgently.",
                    "raw_payload": {"provider": "test"},
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["duplicate"] is False
            assert data["channel"] == "whatsapp"
            assert data["conversation_id"]
            assert data["message_id"]
            assert data["ticket_id"]
            assert data["customer_id"]
            assert data["workflow"]["classification"]["intent"] == "damaged_product"

            detail = await client.get(
                f"/customer-service/conversations/{data['conversation_id']}"
            )
            assert detail.status_code == 200
            messages = detail.json()["messages"]
            assert len(messages) == 1
            assert (
                messages[0]["meta"]["omnichannel"]["external_message_id"] == "message-1"
            )

    finally:
        app.dependency_overrides.pop(get_current_user, None)
