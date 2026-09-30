from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.domains.customer_service.repositories.sla import SLARepository
from app.main import app


class FakeUser:
    def __init__(self, email):
        self.id = uuid4()
        self.email = email
        self.customer_service_role = "owner"


async def _create_ticket_with_sla(client, *, label):
    policy_response = await client.post(
        "/customer-service/sla/policies",
        json={
            "name": f"{label} SLA",
            "priority": "normal",
            "first_response_minutes": 60,
            "resolution_minutes": 1440,
            "is_active": True,
        },
    )
    assert policy_response.status_code == 200

    customer_response = await client.post(
        "/customer-service/customers/",
        json={
            "name": f"{label} Customer",
            "email": f"{uuid4()}@example.com",
            "phone": "+49123456789",
        },
    )
    assert customer_response.status_code == 200

    customer = customer_response.json()

    conversation_response = await client.post(
        "/customer-service/conversations/",
        json={
            "customer_id": customer["id"],
            "channel": "email",
            "subject": f"{label} SLA tenant isolation",
        },
    )
    assert conversation_response.status_code == 200


@pytest.mark.asyncio
async def test_sla_check_only_breaches_current_users_targets():
    user_a = FakeUser("sla-tenant-a@example.com")
    user_b = FakeUser("sla-tenant-b@example.com")

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            app.dependency_overrides[get_current_user] = lambda: user_a

            await _create_ticket_with_sla(
                client,
                label="Tenant A",
            )

            app.dependency_overrides[get_current_user] = lambda: user_b

            await _create_ticket_with_sla(
                client,
                label="Tenant B",
            )

            async with SessionLocal() as db:
                repo = SLARepository(db)

                violations_a = await repo.list_violations(
                    user_id=user_a.id,
                )
                violations_b = await repo.list_violations(
                    user_id=user_b.id,
                )

                assert len(violations_a) == 2
                assert len(violations_b) == 2

                overdue_at = datetime.now(timezone.utc) - timedelta(minutes=5)

                for violation in violations_a:
                    violation.due_at = overdue_at

                for violation in violations_b:
                    violation.due_at = overdue_at

                await db.commit()

                ids_a = {str(violation.id) for violation in violations_a}
                ids_b = {str(violation.id) for violation in violations_b}

            app.dependency_overrides[get_current_user] = lambda: user_a

            response = await client.post("/customer-service/sla/check")

            assert response.status_code == 200

            body = response.json()
            returned_ids = {item["id"] for item in body}

            assert returned_ids == ids_a
            assert returned_ids.isdisjoint(ids_b)

            async with SessionLocal() as db:
                repo = SLARepository(db)

                refreshed_a = await repo.list_violations(
                    user_id=user_a.id,
                )
                refreshed_b = await repo.list_violations(
                    user_id=user_b.id,
                )

                assert {str(item.id) for item in refreshed_a} == ids_a

                assert {str(item.id) for item in refreshed_b} == ids_b

                assert all(item.breached_at is not None for item in refreshed_a)

                assert all(item.breached_at is None for item in refreshed_b)

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
