from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "customer-summary@example.com"


@pytest.mark.asyncio
async def test_customer_summary_counts_conversations_tickets_and_channels():
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
                        "name": "Summary Customer",
                        "email": f"{uuid4()}@example.com",
                        "phone": "+491234",
                    },
                )
            ).json()

            first = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": customer["id"],
                    "channel": "email",
                    "subject": "Email issue",
                },
            )
            assert first.status_code == 200

            second = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": customer["id"],
                    "channel": "chat",
                    "subject": "Chat issue",
                },
            )
            assert second.status_code == 200

            summary = await client.get(
                f"/customer-service/customers/{customer['id']}/summary"
            )

            assert summary.status_code == 200
            data = summary.json()

            assert data["customer_id"] == customer["id"]
            assert data["name"] == "Summary Customer"
            assert data["conversation_count"] == 2
            assert data["ticket_count"] == 2
            assert data["open_ticket_count"] == 2
            assert data["closed_ticket_count"] == 0
            assert data["channels"] == ["chat", "email"]
            assert data["latest_conversation_id"] is not None
            assert data["latest_ticket_id"] is not None
            assert data["first_seen_at"] is not None
            assert data["last_seen_at"] is not None
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_customer_summary_is_user_scoped():
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
                        "name": "Private Summary",
                        "email": f"{uuid4()}@example.com",
                        "phone": "+491234",
                    },
                )
            ).json()

            app.dependency_overrides[get_current_user] = lambda: user_b

            hidden = await client.get(
                f"/customer-service/customers/{customer['id']}/summary"
            )

            assert hidden.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
