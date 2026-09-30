from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "omnichannel-idempotency@example.com"


@pytest.mark.asyncio
async def test_omnichannel_inbound_is_idempotent_by_external_message_id():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    payload = {
        "channel": "instagram",
        "external_account_id": "ig-page-1",
        "external_thread_id": "ig-thread-1",
        "external_message_id": "ig-message-1",
        "external_customer_id": "ig-customer-1",
        "customer_name": "Instagram Customer",
        "customer_email": f"{uuid4()}@example.com",
        "body": "I want a refund for my order.",
    }

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post(
                "/customer-service/omnichannel/inbound", json=payload
            )
            second = await client.post(
                "/customer-service/omnichannel/inbound", json=payload
            )

            assert first.status_code == 200
            assert second.status_code == 200

            first_data = first.json()
            second_data = second.json()

            assert first_data["duplicate"] is False
            assert second_data["duplicate"] is True
            assert second_data["conversation_id"] == first_data["conversation_id"]
            assert second_data["message_id"] == first_data["message_id"]

            detail = await client.get(
                f"/customer-service/conversations/{first_data['conversation_id']}"
            )
            assert detail.status_code == 200
            assert len(detail.json()["messages"]) == 1

    finally:
        app.dependency_overrides.pop(get_current_user, None)
