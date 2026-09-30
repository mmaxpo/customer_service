from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "analytics-test@example.com"


@pytest.mark.asyncio
async def test_customer_service_analytics_summary():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            customer_res = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Analytics Customer",
                    "email": "analytics@example.com",
                    "phone": "+4911112222",
                },
            )
            assert customer_res.status_code == 200
            customer = customer_res.json()

            conversation_res = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": customer["id"],
                    "channel": "email",
                    "subject": "Analytics issue",
                },
            )
            assert conversation_res.status_code == 200

            tickets_res = await client.get("/customer-service/tickets/")
            assert tickets_res.status_code == 200
            ticket = tickets_res.json()[0]

            await client.patch(
                f"/customer-service/tickets/{ticket['id']}",
                json={"priority": "urgent"},
            )

            analytics_res = await client.get("/customer-service/analytics/")
            assert analytics_res.status_code == 200

            data = analytics_res.json()

            assert data["total_customers"] >= 1
            assert data["total_conversations"] >= 1
            assert data["open_tickets"] >= 1
            assert data["urgent_tickets"] >= 1

    finally:
        app.dependency_overrides.pop(get_current_user, None)
