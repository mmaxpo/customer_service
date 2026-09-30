from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "workspace-recommendations@example.com"


@pytest.mark.asyncio
async def test_workspace_recommendations_returns_agent_next_actions():
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
                        "name": "Workspace Customer",
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
                        "subject": "Workspace issue",
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

            res = await client.get(
                f"/customer-service/conversations/{conversation['id']}/workspace-recommendations"
            )

            assert res.status_code == 200
            data = res.json()

            assert data["conversation_id"] == conversation["id"]
            assert data["priority"] == "high"
            assert data["customer_risk_score"] >= 30
            assert "refund_workflow" in data["automation_candidates"]

            types = {item["type"] for item in data["recommended_actions"]}

            assert "reply_customer" in types
            assert "review_refund_request" in types

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_workspace_recommendations_is_user_scoped():
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
                        "name": "Private Workspace",
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
                        "subject": "Private workspace issue",
                    },
                )
            ).json()

            app.dependency_overrides[get_current_user] = lambda: user_b

            hidden = await client.get(
                f"/customer-service/conversations/{conversation['id']}/workspace-recommendations"
            )

            assert hidden.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)
