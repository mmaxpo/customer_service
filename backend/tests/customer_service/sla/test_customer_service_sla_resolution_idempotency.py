from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.domains.customer_service.services.sla import SLAService
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.repositories.sla import SLARepository
from app.domains.customer_service.models import SLATargetType


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "sla-resolution@example.com"
        self.customer_service_role = "owner"


async def _create_ticket(client):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Customer",
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
                "subject": "Need help",
            },
        )
    ).json()

    return conversation["id"]


@pytest.mark.asyncio
async def test_resolution_target_resolution_is_idempotent():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post(
                "/customer-service/sla/policies",
                json={
                    "name": "Normal SLA",
                    "priority": "normal",
                    "first_response_minutes": 10,
                    "resolution_minutes": 60,
                    "is_active": True,
                },
            )

            conversation_id = await _create_ticket(client)

        async with SessionLocal() as db:
            ticket = await TicketRepository(db).get_by_conversation_id(conversation_id)

            service = SLAService(db)

            await service.resolve_resolution_targets(ticket_id=ticket.id)

            await service.resolve_resolution_targets(ticket_id=ticket.id)

            violations = await SLARepository(db).list_violations(user_id=user.id)

            resolution_targets = [
                v for v in violations if v.target_type == SLATargetType.RESOLUTION
            ]

            assert len(resolution_targets) == 1
            assert resolution_targets[0].status == "resolved"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
