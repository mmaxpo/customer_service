from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "dashboard@example.com"


@pytest.mark.asyncio
async def test_dashboard_aggregates_returns_counts():
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
                        "name": "Dashboard Customer",
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
                        "subject": "Dashboard issue",
                    },
                )
            ).json()

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/tags/",
                json={"name": "refund"},
            )

            res = await client.get("/customer-service/dashboard")

            assert res.status_code == 200
            data = res.json()

            assert data["customers"] >= 1
            assert data["open_tickets"] >= 1
            assert data["unassigned_tickets"] >= 1
            assert data["refund_conversations"] >= 1
            assert "workflow_runs" in data
            assert "sla_at_risk" in data

    finally:
        app.dependency_overrides.pop(get_current_user, None)
