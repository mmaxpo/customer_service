from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "omnichannel-outbound-idempotency@example.com"


@pytest.mark.asyncio
async def test_omnichannel_outbound_same_idempotency_key_returns_existing_message_without_duplicate():
    """
    Production harsh case:

    The same outbound request/job is retried after provider success.

    Expected:
        - provider idempotency key is reused
        - second call returns the existing outbound message
        - conversation does not get a duplicate agent message
    """
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-business-outbound-idem-1",
                    "external_thread_id": "thread-outbound-idem-1",
                    "external_message_id": "message-inbound-idem-1",
                    "external_customer_id": "customer-outbound-idem-1",
                    "customer_name": "Outbound Idempotency Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Can you help?",
                },
            )
            assert inbound.status_code == 200
            conversation_id = inbound.json()["conversation_id"]

            payload = {
                "conversation_id": conversation_id,
                "body": "Yes, I can help you.",
                "sender_type": "agent",
                "idempotency_key": "same-outbound-idempotency-key-1",
            }

            first = await client.post(
                "/customer-service/omnichannel/outbound",
                json=payload,
            )
            second = await client.post(
                "/customer-service/omnichannel/outbound",
                json=payload,
            )

            assert first.status_code == 200
            assert second.status_code == 200

            first_data = first.json()
            second_data = second.json()

            assert second_data["message_id"] == first_data["message_id"]
            assert (
                second_data["external_message_id"] == first_data["external_message_id"]
            )

            detail = await client.get(
                f"/customer-service/conversations/{conversation_id}"
            )
            assert detail.status_code == 200

            messages = detail.json()["messages"]
            agent_messages = [
                message
                for message in messages
                if message["sender_type"] == "agent"
                and message["body"] == payload["body"]
            ]

            assert len(messages) == 2
            assert len(agent_messages) == 1
            assert (
                agent_messages[0]["meta"]["omnichannel"]["idempotency_key"]
                == payload["idempotency_key"]
            )

    finally:
        app.dependency_overrides.pop(get_current_user, None)
