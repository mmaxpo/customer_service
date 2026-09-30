from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "customer-risk@example.com"


async def _create_customer_with_conversation(client, *, name: str):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": name,
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
                "subject": f"{name} issue",
            },
        )
    ).json()

    return customer, conversation


@pytest.mark.asyncio
async def test_customer_risk_scores_customer_from_open_ticket_and_tags():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            customer, conversation = await _create_customer_with_conversation(
                client,
                name="Risk Customer",
            )

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/tags/",
                json={"name": "refund"},
            )

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/tags/",
                json={"name": "chargeback"},
            )

            res = await client.get(f"/customer-service/customers/{customer['id']}/risk")

            assert res.status_code == 200
            data = res.json()

            assert data["customer_id"] == customer["id"]
            assert data["risk_score"] >= 60
            assert data["risk_level"] == "high"
            assert "1 open tickets" in data["signals"]
            assert "refund request" in data["signals"]
            assert "chargeback risk" in data["signals"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_customer_risk_leaderboard_orders_highest_risk_first():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            low_customer, _ = await _create_customer_with_conversation(
                client,
                name="Low Risk Customer",
            )

            high_customer, high_conversation = await _create_customer_with_conversation(
                client,
                name="High Risk Customer",
            )

            await client.post(
                f"/customer-service/conversations/{high_conversation['id']}/tags/",
                json={"name": "refund"},
            )

            await client.post(
                f"/customer-service/conversations/{high_conversation['id']}/tags/",
                json={"name": "chargeback"},
            )

            res = await client.get("/customer-service/customers/risk-leaderboard")

            assert res.status_code == 200
            rows = res.json()

            assert rows
            assert rows[0]["customer_id"] == high_customer["id"]
            assert rows[0]["risk_score"] >= rows[-1]["risk_score"]
            assert any(row["customer_id"] == low_customer["id"] for row in rows)

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_customer_risk_is_user_scoped():
    user_a = FakeUser()
    user_b = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user_a

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            customer, _ = await _create_customer_with_conversation(
                client,
                name="Private Risk Customer",
            )

            app.dependency_overrides[get_current_user] = lambda: user_b

            hidden = await client.get(
                f"/customer-service/customers/{customer['id']}/risk"
            )

            assert hidden.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)
