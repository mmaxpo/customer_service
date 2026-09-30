from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "conversation-snapshot@example.com"


@pytest.mark.asyncio
async def test_conversation_intelligence_snapshot_returns_agent_decision_panel():
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
                        "name": "Snapshot Customer",
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
                        "subject": "Snapshot issue",
                    },
                )
            ).json()

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "I am angry and want a refund urgently for order #1001",
                },
            )

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/tags/",
                json={"name": "refund"},
            )

            snapshot = await client.get(
                f"/customer-service/conversations/{conversation['id']}/intelligence/snapshot"
            )

            assert snapshot.status_code == 200
            data = snapshot.json()

            assert data["conversation_id"] == conversation["id"]
            assert data["intent"] == "refund_request"
            assert data["urgency"] == "high"
            assert data["sentiment"] == "negative"
            assert data["open_ticket"] is True
            assert data["customer_risk_score"] >= 30
            assert "refund" in data["tags"]
            assert "review_refund_request" in data["recommended_actions"]
            assert "respond_with_priority" in data["recommended_actions"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_conversation_intelligence_snapshot_is_user_scoped():
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
                        "name": "Private Snapshot",
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
                        "subject": "Private snapshot issue",
                    },
                )
            ).json()

            app.dependency_overrides[get_current_user] = lambda: user_b

            hidden = await client.get(
                f"/customer-service/conversations/{conversation['id']}/intelligence/snapshot"
            )

            assert hidden.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)
