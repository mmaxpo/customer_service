from uuid import uuid4

import pytest

from httpx import ASGITransport, AsyncClient

from app.main import app

from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):

        self.id = uuid4()

        self.email = "ticket-test@example.com"


@pytest.mark.asyncio
async def test_ticket_auto_created_and_can_be_updated():

    user = FakeUser()

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            customer_res = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Ticket Customer",
                    "email": "ticket@example.com",
                    "phone": "+491234567",
                },
            )

            assert customer_res.status_code == 200

            customer = customer_res.json()

            conversation_res = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": customer["id"],
                    "channel": "email",
                    "subject": "Ticket update test",
                },
            )

            assert conversation_res.status_code == 200

            tickets_res = await client.get("/customer-service/tickets/")

            assert tickets_res.status_code == 200

            tickets = tickets_res.json()

            assert len(tickets) >= 1

            ticket = tickets[0]

            assert ticket["title"] == "Ticket update test"

            assert ticket["status"] == "open"

            update_res = await client.patch(
                f"/customer-service/tickets/{ticket['id']}",
                json={
                    "status": "pending",
                    "priority": "high",
                    "assigned_to": "agent-1",
                },
            )

            assert update_res.status_code == 200

            updated = update_res.json()

            assert updated["status"] == "pending"

            assert updated["priority"] == "high"

            assert updated["assigned_to"] == "agent-1"

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_ticket_update_rejects_invalid_status_and_priority():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            customer_res = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Ticket validation customer",
                    "email": f"{uuid4().hex}@example.com",
                },
            )
            assert customer_res.status_code == 200

            conversation_res = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": customer_res.json()["id"],
                    "channel": "email",
                    "subject": "Ticket validation",
                },
            )
            assert conversation_res.status_code == 200

            tickets_res = await client.get("/customer-service/tickets/")
            assert tickets_res.status_code == 200

            ticket = next(
                item
                for item in tickets_res.json()
                if item["conversation_id"] == conversation_res.json()["id"]
            )

            ticket_id = ticket["id"]

            valid_res = await client.patch(
                f"/customer-service/tickets/{ticket_id}",
                json={
                    "status": "pending",
                    "priority": "high",
                },
            )

            assert valid_res.status_code == 200
            assert valid_res.json()["status"] == "pending"
            assert valid_res.json()["priority"] == "high"

            invalid_status = await client.patch(
                f"/customer-service/tickets/{ticket_id}",
                json={
                    "status": "definitely-not-a-status",
                },
            )

            assert invalid_status.status_code == 422

            invalid_priority = await client.patch(
                f"/customer-service/tickets/{ticket_id}",
                json={
                    "priority": "super-mega-critical",
                },
            )

            assert invalid_priority.status_code == 422

            stored = await client.get(f"/customer-service/tickets/{ticket_id}")

            assert stored.status_code == 200
            assert stored.json()["status"] == "pending"
            assert stored.json()["priority"] == "high"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
