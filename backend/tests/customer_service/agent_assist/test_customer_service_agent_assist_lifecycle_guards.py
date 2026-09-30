from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "agent-assist-guards@example.com"


async def create_suggestion(client):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Guard Customer",
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

    return suggestion


@pytest.mark.asyncio
async def test_agent_assist_cannot_edit_or_reject_sent_suggestion():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            suggestion = await create_suggestion(client)
            suggestion_id = suggestion["id"]

            approve_res = await client.post(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/approve"
            )
            assert approve_res.status_code == 200

            send_res = await client.post(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/send"
            )
            assert send_res.status_code == 200
            assert send_res.json()["status"] == "sent"

            edit_res = await client.patch(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}",
                json={
                    "current_suggestion": "Edited after send should fail.",
                    "change_reason": "invalid edit",
                },
            )
            assert edit_res.status_code == 409

            reject_res = await client.post(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/reject"
            )
            assert reject_res.status_code == 409

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_agent_assist_cannot_send_rejected_suggestion():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            suggestion = await create_suggestion(client)
            suggestion_id = suggestion["id"]

            reject_res = await client.post(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/reject"
            )
            assert reject_res.status_code == 200
            assert reject_res.json()["status"] == "rejected"

            send_res = await client.post(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/send"
            )
            assert send_res.status_code == 409

    finally:
        app.dependency_overrides.pop(get_current_user, None)
