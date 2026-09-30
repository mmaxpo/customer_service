from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "agent-assist-timeline@example.com"


@pytest.mark.asyncio
async def test_agent_assist_lifecycle_events_appear_in_timeline():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Timeline Event Customer",
                        "email": f"{uuid4()}@example.com",
                        "phone": "+49123456789",
                    },
                )
            ).json()

            conversation = (
                await client.post(
                    "/customer-service/conversations/",
                    json={
                        "customer_id": customer["id"],
                        "channel": "email",
                        "subject": "Damaged item",
                    },
                )
            ).json()

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "My item arrived damaged and broken.",
                },
            )

            suggestion = (
                await client.post(
                    f"/customer-service/conversations/{conversation['id']}/agent-assist/reply-suggestion"
                )
            ).json()

            suggestion_id = suggestion["id"]

            await client.patch(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}",
                json={
                    "current_suggestion": "Please send your order number and a photo.",
                    "change_reason": "shorter reply",
                },
            )

            await client.post(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/approve"
            )

            await client.post(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/send"
            )

            detail = (
                await client.get(
                    f"/customer-service/conversations/{conversation['id']}"
                )
            ).json()

            events = [
                message["meta"].get("event")
                for message in detail["messages"]
                if message.get("meta")
            ]

            assert "agent_assist.suggestion_generated" in events
            assert "agent_assist.suggestion_edited" in events
            assert "agent_assist.suggestion_approved" in events
            assert "agent_assist.suggestion_sent" in events

    finally:
        app.dependency_overrides.pop(get_current_user, None)
