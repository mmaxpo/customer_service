from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.domains.customer_service.models import SLATargetType
from app.domains.customer_service.repositories.sla import SLARepository
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.services.sla import SLAService
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "sla-breach-history@example.com"
        self.customer_service_role = "owner"


async def _create_ticket(client):
    await client.post(
        "/customer-service/sla/policies",
        json={
            "name": "Fast SLA",
            "priority": "normal",
            "first_response_minutes": 1,
            "resolution_minutes": 2,
            "is_active": True,
        },
    )

    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Breach Customer",
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
                "subject": "Breach history issue",
            },
        )
    ).json()

    return conversation["id"]


@pytest.mark.asyncio
async def test_breached_first_response_target_keeps_breached_at_after_resolution():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            conversation_id = await _create_ticket(client)

        async with SessionLocal() as db:
            ticket = await TicketRepository(db).get_by_conversation_id(conversation_id)
            repo = SLARepository(db)

            violations = await repo.list_violations(user_id=user.id)
            first_response = next(
                item
                for item in violations
                if item.target_type == SLATargetType.FIRST_RESPONSE
            )

            first_response.due_at = datetime.now(timezone.utc) - timedelta(minutes=5)
            await db.commit()

            breached = await SLAService(db).check_breaches(user_id=user.id)

            breached_first_response = next(
                item for item in breached if item.id == first_response.id
            )

            assert breached_first_response.breached_at is not None
            breached_at = breached_first_response.breached_at

            resolved = await SLAService(db).resolve_first_response_targets(
                ticket_id=ticket.id
            )

            resolved_first_response = next(
                item for item in resolved if item.id == first_response.id
            )

            assert resolved_first_response.status == "resolved"
            assert resolved_first_response.breached_at == breached_at

    finally:
        app.dependency_overrides.pop(get_current_user, None)
