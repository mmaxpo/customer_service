from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.services.sla import SLAService
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "sla-target-idempotency@example.com"
        self.customer_service_role = "owner"


async def _create_policy_and_ticket(client):
    policy = await client.post(
        "/customer-service/sla/policies",
        json={
            "name": "Normal SLA",
            "priority": "normal",
            "first_response_minutes": 10,
            "resolution_minutes": 60,
            "is_active": True,
        },
    )
    assert policy.status_code == 200

    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "SLA Customer",
                "email": f"{uuid4()}@example.com",
                "phone": "+49123456789",
            },
        )
    ).json()

    conversation = await client.post(
        "/customer-service/conversations/",
        json={
            "customer_id": customer["id"],
            "channel": "email",
            "subject": "Need help",
        },
    )
    assert conversation.status_code == 200

    return conversation.json()["id"]


@pytest.mark.asyncio
async def test_sla_targets_are_idempotent_for_same_ticket():
    """
    Production hardening:

    If ticket creation/retry calls SLA target creation more than once,
    the ticket must still have exactly one first-response target and one
    resolution target.
    """
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            conversation_id = await _create_policy_and_ticket(client)

        async with SessionLocal() as db:
            ticket = await TicketRepository(db).get_by_conversation_id(conversation_id)
            ticket_id = ticket.id

            first = await SLAService(db).create_targets_for_ticket(ticket=ticket)
            second = await SLAService(db).create_targets_for_ticket(ticket=ticket)

            assert len(first) == 2
            assert len(second) == 2

            violations = await SLAService(db).list_violations(user_id=user.id)

            ticket_violations = [
                item for item in violations if str(item.ticket_id) == str(ticket_id)
            ]

            first_response = [
                item
                for item in ticket_violations
                if item.target_type == "first_response"
            ]
            resolution = [
                item for item in ticket_violations if item.target_type == "resolution"
            ]

            assert len(first_response) == 1
            assert len(resolution) == 1

    finally:
        app.dependency_overrides.pop(get_current_user, None)
