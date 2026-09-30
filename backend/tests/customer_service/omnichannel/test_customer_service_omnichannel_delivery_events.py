from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    id = uuid4()


@pytest.mark.asyncio
async def test_omnichannel_delivery_event_updates_outbound_message_status():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-business-delivery-1",
                    "external_thread_id": "thread-delivery-1",
                    "external_message_id": "message-inbound-delivery-1",
                    "external_customer_id": "customer-delivery-1",
                    "customer_name": "Delivery Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Can you help me?",
                },
            )
            assert inbound.status_code == 200

            outbound = await client.post(
                "/customer-service/omnichannel/outbound",
                json={
                    "conversation_id": inbound.json()["conversation_id"],
                    "body": "Yes, I can help.",
                    "sender_type": "agent",
                    "idempotency_key": "delivery-outbound-1",
                },
            )
            assert outbound.status_code == 200

            delivery = await client.post(
                "/customer-service/omnichannel/delivery-events",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-business-delivery-1",
                    "external_message_id": outbound.json()["external_message_id"],
                    "delivery_status": "delivered",
                    "raw_payload": {"provider_status": "delivered"},
                },
            )

            assert delivery.status_code == 200
            assert delivery.json()["updated"] is True
            assert delivery.json()["delivery_status"] == "delivered"
    finally:
        app.dependency_overrides.clear()
