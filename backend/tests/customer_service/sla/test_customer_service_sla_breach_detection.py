from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    SLAViolation,
    SLAViolationStatus,
)
from app.domains.customer_service.services.sla import SLAService


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "sla-hardening@example.com"
        self.customer_service_role = "owner"


async def _create_ticket_with_sla(client):
    await client.post(
        "/customer-service/sla/policies",
        json={
            "name": "Normal SLA",
            "priority": "normal",
            "first_response_minutes": 60,
            "resolution_minutes": 1440,
            "is_active": True,
        },
    )

    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "SLA Customer",
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
            "subject": "SLA issue",
        },
    )

    ticket = (await client.get("/customer-service/tickets/")).json()[0]
    return ticket


@pytest.mark.asyncio
async def test_check_breaches_marks_overdue_targets():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            ticket = await _create_ticket_with_sla(client)

            async with SessionLocal() as db:
                result = await db.execute(
                    select(SLAViolation).where(SLAViolation.ticket_id == ticket["id"])
                )

                violations = result.scalars().all()

                for v in violations:
                    v.due_at = datetime.now(timezone.utc) - timedelta(minutes=5)

                await db.commit()

                breached = await SLAService(db).check_breaches(user_id=user.id)

                result = await db.execute(
                    select(SLAViolation).where(SLAViolation.ticket_id == ticket["id"])
                )

                refreshed = result.scalars().all()

                assert len(refreshed) == 2
                assert all(v.breached_at is not None for v in refreshed)

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_resolve_first_response_targets():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            ticket = await _create_ticket_with_sla(client)

            async with SessionLocal() as db:
                resolved = await SLAService(db).resolve_first_response_targets(
                    ticket_id=ticket["id"]
                )

                assert len(resolved) == 1
                assert resolved[0].status == SLAViolationStatus.RESOLVED

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_resolve_resolution_targets():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            ticket = await _create_ticket_with_sla(client)

            async with SessionLocal() as db:
                resolved = await SLAService(db).resolve_resolution_targets(
                    ticket_id=ticket["id"]
                )

                assert len(resolved) == 1
                assert resolved[0].status == SLAViolationStatus.RESOLVED

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_resolved_targets_do_not_breach():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            ticket = await _create_ticket_with_sla(client)

            async with SessionLocal() as db:
                await SLAService(db).resolve_first_response_targets(
                    ticket_id=ticket["id"]
                )

                result = await db.execute(
                    select(SLAViolation).where(SLAViolation.ticket_id == ticket["id"])
                )

                violations = result.scalars().all()

                for v in violations:
                    v.due_at = datetime.now(timezone.utc) - timedelta(minutes=10)

                await db.commit()

                breached = await SLAService(db).check_breaches(user_id=user.id)

                assert all(item.status == SLAViolationStatus.OPEN for item in breached)

    finally:
        app.dependency_overrides.pop(get_current_user, None)
