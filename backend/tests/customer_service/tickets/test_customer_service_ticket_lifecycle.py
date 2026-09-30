from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user, get_current_verified_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "ticket-lifecycle@example.com"
        self.role = "owner"


@pytest.mark.asyncio
async def test_ticket_lifecycle_updates_inbox():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_verified_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            customer_res = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Lifecycle Customer",
                    "email": "lifecycle@example.com",
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
                    "subject": "Lifecycle ticket issue",
                },
            )
            assert conversation_res.status_code == 200

            inbox_res = await client.get("/customer-service/inbox/")
            assert inbox_res.status_code == 200

            inbox_item = inbox_res.json()[0]
            ticket_id = inbox_item["ticket"]["id"]

            tag_res = await client.post(
                f"/customer-service/conversations/{inbox_item['conversation_id']}/tags/",
                json={"name": "vip"},
            )
            assert tag_res.status_code == 200

            update_res = await client.patch(
                f"/customer-service/tickets/{ticket_id}",
                json={
                    "priority": "high",
                    "assigned_to": "agent-1",
                },
            )
            assert update_res.status_code == 200
            assert update_res.json()["priority"] == "high"
            assert update_res.json()["assigned_to"] == "agent-1"

            close_res = await client.post(
                f"/customer-service/tickets/{ticket_id}/close"
            )
            assert close_res.status_code == 200
            assert close_res.json()["status"] == "closed"

            inbox_after_res = await client.get("/customer-service/inbox/")
            assert inbox_after_res.status_code == 200

            inbox_after = inbox_after_res.json()[0]
            assert inbox_after["ticket"]["status"] == "closed"
            assert inbox_after["ticket"]["priority"] == "high"
            assert inbox_after["tags"] == ["vip"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_verified_user, None)
