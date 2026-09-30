from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.domains.customer_service.models import SLATargetType
from app.domains.customer_service.repositories.sla import SLARepository
from app.domains.customer_service.services.sla import SLAService
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "sla-check-breaches-idempotency@example.com"
        self.customer_service_role = "owner"


async def _create_ticket_with_due_sla(client):
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

    await client.post(
        "/customer-service/conversations/",
        json={
            "customer_id": customer["id"],
            "channel": "email",
            "subject": "Breach idempotency issue",
        },
    )


@pytest.mark.asyncio
async def test_check_breaches_is_idempotent_for_already_breached_targets():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await _create_ticket_with_due_sla(client)

        async with SessionLocal() as db:
            repo = SLARepository(db)

            violations = await repo.list_violations(user_id=user.id)
            first_response = next(
                item
                for item in violations
                if item.target_type == SLATargetType.FIRST_RESPONSE
            )

            first_response.due_at = datetime.now(timezone.utc) - timedelta(minutes=5)
            await db.commit()

            first_run = await SLAService(db).check_breaches(user_id=user.id)
            assert any(item.id == first_response.id for item in first_run)

            refreshed = await repo.list_violations(user_id=user.id)
            breached_target = next(
                item for item in refreshed if item.id == first_response.id
            )
            first_breached_at = breached_target.breached_at

            assert first_breached_at is not None

            second_run = await SLAService(db).check_breaches(user_id=user.id)
            third_run = await SLAService(db).check_breaches(user_id=user.id)

            assert all(item.id != first_response.id for item in second_run)
            assert all(item.id != first_response.id for item in third_run)

            refreshed_again = await repo.list_violations(user_id=user.id)
            breached_target_again = next(
                item for item in refreshed_again if item.id == first_response.id
            )

            assert breached_target_again.breached_at == first_breached_at

    finally:
        app.dependency_overrides.pop(get_current_user, None)
