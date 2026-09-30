from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "customer-360@example.com"


@pytest.mark.asyncio
async def test_customer_360_returns_sidebar_bundle():
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
                        "name": "360 Customer",
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
                        "subject": "360 issue",
                    },
                )
            ).json()

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "I need help with order #1001",
                },
            )

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/tags/",
                json={"name": "vip"},
            )

            res = await client.get(f"/customer-service/customers/{customer['id']}/360")

            assert res.status_code == 200
            data = res.json()

            assert data["customer"]["id"] == customer["id"]
            assert data["summary"]["customer_id"] == customer["id"]
            assert data["recent_conversations"]
            assert data["recent_tickets"]
            assert data["recent_activity"]
            assert "vip" in data["tags"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_customer_360_is_user_scoped():
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
                        "name": "Private 360",
                        "email": f"{uuid4()}@example.com",
                        "phone": "+491234",
                    },
                )
            ).json()

            app.dependency_overrides[get_current_user] = lambda: user_b

            hidden = await client.get(
                f"/customer-service/customers/{customer['id']}/360"
            )

            assert hidden.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)
