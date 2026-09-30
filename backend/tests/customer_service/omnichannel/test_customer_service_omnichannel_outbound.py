from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "omnichannel-outbound@example.com"


@pytest.mark.asyncio
async def test_omnichannel_outbound_sends_provider_message_and_records_agent_message():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    customer_email = f"{uuid4()}@example.com"

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-business-outbound-1",
                    "external_thread_id": "thread-outbound-1",
                    "external_message_id": "message-inbound-1",
                    "external_customer_id": "customer-outbound-1",
                    "customer_name": "Outbound Customer",
                    "customer_email": customer_email,
                    "body": "Where is my order?",
                },
            )
            assert inbound.status_code == 200
            conversation_id = inbound.json()["conversation_id"]

            outbound = await client.post(
                "/customer-service/omnichannel/outbound",
                json={
                    "conversation_id": conversation_id,
                    "body": "I checked your order and I am helping you now.",
                    "sender_type": "agent",
                    "idempotency_key": "outbound-message-1",
                },
            )

            assert outbound.status_code == 200
            data = outbound.json()
            assert data["conversation_id"] == conversation_id
            assert data["external_message_id"] == "outbound-message-1"
            assert data["channel"] == "whatsapp"
            assert data["external_account_id"] == "wa-business-outbound-1"
            assert data["external_thread_id"] == "thread-outbound-1"
            assert data["delivery_status"] == "sent"

            detail = await client.get(
                f"/customer-service/conversations/{conversation_id}"
            )
            assert detail.status_code == 200
            messages = detail.json()["messages"]
            assert len(messages) == 2
            assert messages[-1]["sender_type"] == "agent"
            assert messages[-1]["meta"]["omnichannel"]["direction"] == "outbound"
            assert (
                messages[-1]["meta"]["omnichannel"]["external_message_id"]
                == "outbound-message-1"
            )

    finally:
        app.dependency_overrides.pop(get_current_user, None)
