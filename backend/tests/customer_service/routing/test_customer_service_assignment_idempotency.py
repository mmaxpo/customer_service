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
        self.email = "assignment-idempotency@example.com"
        self.customer_service_role = "owner"


async def _create_ticket(client):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Assignment Customer",
                "email": f"{uuid4()}@example.com",
                "phone": "+49123456789",
            },
        )
    ).json()

    conversation = (
        await client.post(
            "/customer-service/conversations/",
            json={
                "customer_id": customer["id"],
                "channel": "email",
                "subject": "Assignment issue",
            },
        )
    ).json()

    return conversation["id"]


@pytest.mark.asyncio
async def test_assigning_same_ticket_to_same_agent_is_idempotent():
    user = FakeUser()
    assignee = uuid4()

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            conversation_id = await _create_ticket(client)

        async with SessionLocal() as db:
            ticket = await TicketRepository(db).get_by_conversation_id(conversation_id)
            ticket_id = ticket.id

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.post(
                f"/customer-service/tickets/{ticket_id}/assign",
                params={"assigned_to": str(assignee)},
            )
            second = await client.post(
                f"/customer-service/tickets/{ticket_id}/assign",
                params={"assigned_to": str(assignee)},
            )

            assert first.status_code == 200
            assert second.status_code == 200
            assert first.json()["id"] == second.json()["id"]

        async with SessionLocal() as db:
            assignment_result = await db.execute(
                select(TicketAssignment).where(
                    TicketAssignment.ticket_id == ticket_id,
                    TicketAssignment.is_active.is_(True),
                )
            )
            active_assignments = list(assignment_result.scalars().all())

            assert len(active_assignments) == 1
            assert str(active_assignments[0].assigned_to) == str(assignee)

            messages_result = await db.execute(
                select(ConversationMessage).where(
                    ConversationMessage.conversation_id == conversation_id,
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
