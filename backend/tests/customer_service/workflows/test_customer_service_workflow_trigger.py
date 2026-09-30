from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "workflow-trigger@example.com"


async def create_customer_and_conversation(client, subject: str):
    customer_res = await client.post(
        "/customer-service/customers/",
        json={
            "name": "Workflow Trigger Customer",
            "email": f"{uuid4()}@example.com",
            "phone": "+49123456789",
        },
    )
    assert customer_res.status_code == 200
    customer = customer_res.json()

    conversation_res = await client.post(
        "/customer-service/conversations/",
        json={
            "customer_id": customer["id"],
            "channel": "email",
            "subject": subject,
        },
    )
    assert conversation_res.status_code == 200

    inbox_res = await client.get("/customer-service/inbox/")
    assert inbox_res.status_code == 200

    conversation = conversation_res.json()
    ticket = next(
        item["ticket"]
        for item in inbox_res.json()
        if item["conversation_id"] == conversation["id"]
    )

    return conversation["id"], ticket["id"]


@pytest.mark.asyncio
async def test_damaged_message_sets_ticket_priority_to_urgent():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            conversation_id, ticket_id = await create_customer_and_conversation(
                client,
                "Damaged product issue",
            )

            message_res = await client.post(
                f"/customer-service/conversations/{conversation_id}/messages",
                json={
                    "sender_type": "customer",
                    "body": "My product arrived damaged and broken.",
                },
            )
            assert message_res.status_code == 200

            ticket_res = await client.get(f"/customer-service/tickets/{ticket_id}")
            assert ticket_res.status_code == 200
            assert ticket_res.json()["priority"] == "urgent"

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_refund_message_sets_ticket_priority_to_high():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            conversation_id, ticket_id = await create_customer_and_conversation(
                client,
                "Refund request",
            )

            message_res = await client.post(
                f"/customer-service/conversations/{conversation_id}/messages",
                json={
                    "sender_type": "customer",
                    "body": "I want a refund for this order.",
                },
            )
            assert message_res.status_code == 200

            ticket_res = await client.get(f"/customer-service/tickets/{ticket_id}")
            assert ticket_res.status_code == 200
            assert ticket_res.json()["priority"] == "high"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
