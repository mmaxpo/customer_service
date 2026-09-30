from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    id = uuid4()


@pytest.mark.asyncio
async def test_omnichannel_delivery_event_history_is_persisted():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-business-history-1",
                    "external_thread_id": "thread-history-1",
                    "external_message_id": "message-inbound-history-1",
                    "external_customer_id": "customer-history-1",
                    "customer_name": "History Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Hello",
                },
            )
            assert inbound.status_code == 200

            outbound = await client.post(
                "/customer-service/omnichannel/outbound",
                json={
                    "conversation_id": inbound.json()["conversation_id"],
                    "body": "Hello, how can I help?",
                    "sender_type": "agent",
                    "idempotency_key": "history-outbound-1",
                },
            )
            assert outbound.status_code == 200

            external_message_id = outbound.json()["external_message_id"]

            delivered = await client.post(
                "/customer-service/omnichannel/delivery-events",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-business-history-1",
                    "external_message_id": external_message_id,
                    "delivery_status": "delivered",
                    "raw_payload": {"provider_status": "delivered"},
                    "meta": {"source": "test"},
                },
            )
            assert delivered.status_code == 200
            assert delivered.json()["updated"] is True

            read = await client.post(
                "/customer-service/omnichannel/delivery-events",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-business-history-1",
                    "external_message_id": external_message_id,
                    "delivery_status": "read",
                    "raw_payload": {"provider_status": "read"},
                },
            )
            assert read.status_code == 200
            assert read.json()["updated"] is True
    finally:
        app.dependency_overrides.clear()
