from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


async def _conversation(client):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Phase2 Customer",
                "email": f"{uuid4()}@test.com",
                "phone": "1",
            },
        )
    ).json()

    conversation = (
        await client.post(
            "/customer-service/conversations/",
            json={
                "customer_id": customer["id"],
                "channel": "chat",
                "subject": "refund",
            },
        )
    ).json()

    await client.post(
        f"/customer-service/conversations/{conversation['id']}/messages",
        json={
            "sender_type": "customer",
            "body": "I want a refund for order #1001",
        },
    )

    return conversation


@pytest.mark.asyncio
async def test_conversation_summary_generation_endpoint():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            conversation = await _conversation(client)

            response = await client.post(
                f"/customer-service/conversations/{conversation['id']}/summary/generate"
            )

            assert response.status_code == 200

            data = response.json()

            assert "refund" in data["summary"].lower()
            assert data["intent"] is not None
            assert "entities" in data

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_reply_quality_trends_endpoint():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/customer-service/analytics/reply-quality/trends"
            )

            assert response.status_code == 200

            data = response.json()

            assert "last_7_days" in data
            assert "last_30_days" in data
            assert "acceptance_rate" in data["last_7_days"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)
