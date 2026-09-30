from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.domains.customer_service.models import SLATargetType
from app.domains.customer_service.repositories.sla import SLARepository
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.schemas.conversations import (
    ConversationMessageCreate,
    SenderType,
)
from app.domains.customer_service.services.inbox import InboxService
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "sla-first-response-rules@example.com"
        self.customer_service_role = "owner"


async def _create_ticket(client):
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


async def _first_response_statuses(db, user_id):
    violations = await SLARepository(db).list_violations(user_id=user_id)
    return [
        item.status
        for item in violations
        if item.target_type == SLATargetType.FIRST_RESPONSE
    ]


@pytest.mark.asyncio
async def test_customer_message_does_not_resolve_first_response_sla():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            conversation_id = await _create_ticket(client)

        async with SessionLocal() as db:
            await InboxService(db).add_message(
                conversation_id=conversation_id,
                payload=ConversationMessageCreate(
                    sender_type=SenderType.CUSTOMER,
                    body="Adding more info",
                ),
            )

            statuses = await _first_response_statuses(db, user.id)

            assert statuses == ["open"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("sender_type", [SenderType.AGENT, SenderType.AI])
async def test_agent_or_ai_message_resolves_first_response_sla(sender_type):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            conversation_id = await _create_ticket(client)

        async with SessionLocal() as db:
            await InboxService(db).add_message(
                conversation_id=conversation_id,
                payload=ConversationMessageCreate(
                    sender_type=sender_type,
                    body="We are checking this for you",
                ),
            )

            statuses = await _first_response_statuses(db, user.id)

            assert statuses == ["resolved"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("sender_type", [SenderType.SYSTEM, SenderType.INTERNAL_NOTE])
async def test_system_or_internal_note_does_not_resolve_first_response_sla(sender_type):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            conversation_id = await _create_ticket(client)

        async with SessionLocal() as db:
            await InboxService(db).add_message(
                conversation_id=conversation_id,
                payload=ConversationMessageCreate(
                    sender_type=sender_type,
                    body="Internal/system update",
                ),
            )

            statuses = await _first_response_statuses(db, user.id)

            assert statuses == ["open"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)
