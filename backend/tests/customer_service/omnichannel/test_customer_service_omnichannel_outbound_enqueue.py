from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    id = uuid4()


@pytest.mark.asyncio
async def test_omnichannel_outbound_can_enqueue_delivery_job():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-business-queue-1",
                    "external_thread_id": "thread-queue-1",
                    "external_message_id": "message-inbound-queue-1",
                    "external_customer_id": "customer-queue-1",
                    "customer_name": "Queue Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Hello",
                },
            )
            assert inbound.status_code == 200

            response = await client.post(
                "/customer-service/omnichannel/outbound/enqueue",
                json={
                    "conversation_id": inbound.json()["conversation_id"],
                    "body": "Queued reply",
                    "sender_type": "agent",
                    "idempotency_key": "queue-outbound-1",
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert data["job_type"] == "customer_service.omnichannel.outbound.send"
        assert data["status"] == "queued"
        assert data["payload"]["channel"] == "whatsapp"
        assert data["payload"]["external_account_id"] == "wa-business-queue-1"
        assert data["payload"]["external_thread_id"] == "thread-queue-1"
        assert data["payload"]["body"] == "Queued reply"
    finally:
        app.dependency_overrides.clear()
