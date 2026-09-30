from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "routing@example.com"
        self.customer_service_role = "owner"


async def _create_ticket(client, subject="Routing ticket"):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Routing Customer",
                "email": f"{uuid4()}@example.com",
                "phone": "+491234",
            },
        )
    ).json()

    await client.post(
        "/customer-service/conversations/",
        json={
            "customer_id": customer["id"],
            "channel": "email",
            "subject": subject,
        },
    )

    tickets = (await client.get("/customer-service/tickets/")).json()
    return tickets[0]


@pytest.mark.asyncio
async def test_auto_assign_ticket_chooses_least_loaded_candidate():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        assignee_busy = uuid4()
        assignee_free = uuid4()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            busy_ticket = await _create_ticket(client, "Busy assignee ticket")
            assign_busy = await client.post(
                f"/customer-service/tickets/{busy_ticket['id']}/assign",
                params={"assigned_to": str(assignee_busy)},
            )
            assert assign_busy.status_code == 200

            target_ticket = await _create_ticket(client, "Target routing ticket")

            routed = await client.post(
                f"/customer-service/tickets/{target_ticket['id']}/auto-assign",
                json={
                    "candidate_assignee_ids": [
                        str(assignee_busy),
                        str(assignee_free),
                    ],
                    "strategy": "least_loaded",
                },
            )

            assert routed.status_code == 200
            body = routed.json()
            assert body["decision"]["assigned_to"] == str(assignee_free)
            assert body["decision"]["candidate_loads"][str(assignee_busy)] >= 1
            assert body["decision"]["candidate_loads"][str(assignee_free)] == 0

            updated = (
                await client.get(
                    f"/customer-service/tickets/{target_ticket['id']}",
                )
            ).json()
            assert updated["assigned_to"] == str(assignee_free)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
