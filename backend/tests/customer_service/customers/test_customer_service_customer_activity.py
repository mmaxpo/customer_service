from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "customer-activity@example.com"


@pytest.mark.asyncio
async def test_customer_activity_returns_customer_conversation_ticket_and_message_events():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Activity Customer",
                        "email": f"{uuid4()}@example.com",
                        "phone": "+491234",
                    },
                )
            ).json()

            conversation = (
                await client.post(
                    "/customer-service/conversations/",
                    json={
                        "customer_id": customer["id"],
                        "channel": "email",
                        "subject": "Activity issue",
                    },
                )
            ).json()

            message = await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "I need help with order #1001",
                },
            )
            assert message.status_code == 200

            activity = await client.get(
                f"/customer-service/customers/{customer['id']}/activity"
            )

            assert activity.status_code == 200
            events = activity.json()
            types = {event["type"] for event in events}

            assert "customer.created" in types
            assert "conversation.created" in types
            assert "ticket.created" in types
            assert "message.created" in types

            assert any(
                event["entity_type"] == "conversation"
                and event["entity_id"] == conversation["id"]
                for event in events
            )

            timestamps = [event["timestamp"] for event in events]
            assert timestamps == sorted(timestamps, reverse=True)

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_customer_activity_is_user_scoped():
    user_a = FakeUser()
    user_b = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user_a

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Private Activity",
                        "email": f"{uuid4()}@example.com",
                        "phone": "+491234",
                    },
                )
            ).json()

            app.dependency_overrides[get_current_user] = lambda: user_b

            hidden = await client.get(
                f"/customer-service/customers/{customer['id']}/activity"
            )

            assert hidden.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)
