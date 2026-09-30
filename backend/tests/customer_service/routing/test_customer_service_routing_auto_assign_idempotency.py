import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    ConversationMessage,
    MessageSenderType,
    TicketAssignment,
)
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "routing-auto-assign-idempotency@example.com"
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
async def test_concurrent_auto_assign_same_ticket_is_idempotent():
    user = FakeUser()
    assignee = uuid4()

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            ticket = await _create_ticket(client, "Concurrent same-ticket auto assign")

        async def auto_assign_once():
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                return await client.post(
                    f"/customer-service/tickets/{ticket['id']}/auto-assign",
                    json={
                        "candidate_assignee_ids": [str(assignee)],
                        "strategy": "least_loaded",
                    },
                )

        first, second = await asyncio.gather(
            auto_assign_once(),
            auto_assign_once(),
        )

        assert first.status_code == 200
        assert second.status_code == 200

        assert first.json()["assignment_id"] == second.json()["assignment_id"]

        async with SessionLocal() as db:
            stored_ticket = await TicketRepository(db).get(
                user.id,
                ticket["id"],
            )

            assignment_result = await db.execute(
                select(TicketAssignment).where(
                    TicketAssignment.ticket_id == stored_ticket.id,
                    TicketAssignment.is_active.is_(True),
                )
            )
            active_assignments = list(assignment_result.scalars().all())

            assert len(active_assignments) == 1
            assert str(active_assignments[0].assigned_to) == str(assignee)

            messages_result = await db.execute(
                select(ConversationMessage).where(
                    ConversationMessage.conversation_id
                    == stored_ticket.conversation_id,
                    ConversationMessage.sender_type == MessageSenderType.SYSTEM,
                )
            )
            assignment_messages = [
                message
                for message in messages_result.scalars().all()
                if (message.meta or {}).get("event") == "ticket.assigned"
            ]

            assert len(assignment_messages) == 1

    finally:
        app.dependency_overrides.pop(get_current_user, None)
