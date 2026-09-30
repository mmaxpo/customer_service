from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "message-meta@example.com"


@pytest.mark.asyncio
async def test_message_metadata_contains_workflow_classification():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            customer_res = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Meta Customer",
                    "email": "meta@example.com",
                    "phone": "+49123456789",
                },
            )
            customer = customer_res.json()

            conversation_res = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": customer["id"],
                    "channel": "email",
                    "subject": "Metadata test",
                },
            )
            conversation = conversation_res.json()

            message_res = await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "My item arrived damaged and broken.",
                },
            )

            assert message_res.status_code == 200

            message = message_res.json()
            workflow = message["meta"]["workflow"]

            assert workflow["classification"]["intent"] == "damaged_product"
            assert workflow["classification"]["confidence"] == 0.9
            assert workflow["action"]["ticket_priority"] == "urgent"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
