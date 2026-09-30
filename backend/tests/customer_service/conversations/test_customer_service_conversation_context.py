from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "context@example.com"


@pytest.mark.asyncio
async def test_conversation_context_returns_support_workspace_bundle():
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
                        "name": "Context Customer",
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
                        "subject": "Context issue",
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

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/tags/",
                json={"name": "refund"},
            )

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/intelligence/analyze",
                json={"force_refresh": True},
            )

            context = await client.get(
                f"/customer-service/conversations/{conversation['id']}/context"
            )

            assert context.status_code == 200
            data = context.json()

            assert data["conversation"]["id"] == conversation["id"]
            assert data["customer"]["id"] == customer["id"]
            assert data["ticket"] is not None
            assert [tag["name"] for tag in data["tags"]] == ["refund"]
            assert data["insights"]
            assert data["latest_insight"]["intent"] == "refund_request"
            assert "timeline" in data
            assert any(item["type"] == "message" for item in data["timeline"])
            assert "sla" in data
            assert "violations" in data["sla"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_conversation_context_is_user_scoped():
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
                        "name": "Private Customer",
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
                        "subject": "Private issue",
                    },
                )
            ).json()

            app.dependency_overrides[get_current_user] = lambda: user_b

            hidden = await client.get(
                f"/customer-service/conversations/{conversation['id']}/context"
            )

            assert hidden.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
