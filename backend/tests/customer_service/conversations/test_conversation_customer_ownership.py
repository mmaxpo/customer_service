from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    Customer,
    SLAViolation,
    Ticket,
)
from app.main import app


class FakeUser:
    def __init__(self, email: str):
        self.id = uuid4()
        self.email = email


async def _delete_conversation_chain(
    conversation_ids: list[str],
) -> None:
    if not conversation_ids:
        return

    async with SessionLocal() as db:
        ticket_ids = list(
            (
                await db.execute(
                    select(Ticket.id).where(
                        Ticket.conversation_id.in_(conversation_ids)
                    )
                )
            )
            .scalars()
            .all()
        )

        if ticket_ids:
            await db.execute(
                delete(SLAViolation).where(SLAViolation.ticket_id.in_(ticket_ids))
            )

            await db.execute(delete(Ticket).where(Ticket.id.in_(ticket_ids)))

        await db.execute(
            delete(ConversationMessage).where(
                ConversationMessage.conversation_id.in_(conversation_ids)
            )
        )

        await db.execute(
            delete(Conversation).where(Conversation.id.in_(conversation_ids))
        )

        await db.commit()


@pytest.mark.asyncio
async def test_conversation_create_requires_owned_customer():
    owner = FakeUser("conversation-owner@example.com")
    foreign = FakeUser("conversation-foreign@example.com")

    owner_customer_id = None
    foreign_customer_id = None
    created_conversation_ids: list[str] = []

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            app.dependency_overrides[get_current_user] = lambda: owner

            owner_customer = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Owner Customer",
                    "email": f"{uuid4().hex}@example.com",
                },
            )

            assert owner_customer.status_code == 200
            owner_customer_id = owner_customer.json()["id"]

            app.dependency_overrides[get_current_user] = lambda: foreign

            foreign_customer = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Foreign Customer",
                    "email": f"{uuid4().hex}@example.com",
                    "phone": "+499999999999",
                },
            )

            assert foreign_customer.status_code == 200
            foreign_customer_id = foreign_customer.json()["id"]

            app.dependency_overrides[get_current_user] = lambda: owner

            valid = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": owner_customer_id,
                    "channel": "chat",
                    "subject": "Owned customer conversation",
                },
            )

            assert valid.status_code == 200, valid.text

            valid_id = valid.json()["id"]
            created_conversation_ids.append(valid_id)

            foreign_attempt = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": foreign_customer_id,
                    "channel": "chat",
                    "subject": "Foreign customer probe",
                },
            )

            assert foreign_attempt.status_code == 404
            assert foreign_attempt.json() == {"detail": "Customer not found"}

            unknown_customer_id = uuid4()

            unknown_attempt = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": str(unknown_customer_id),
                    "channel": "chat",
                    "subject": "Unknown customer probe",
                },
            )

            assert unknown_attempt.status_code == 404
            assert unknown_attempt.json() == {"detail": "Customer not found"}

            async with SessionLocal() as db:
                foreign_rows = list(
                    (
                        await db.execute(
                            select(Conversation).where(
                                Conversation.user_id == owner.id,
                                Conversation.customer_id == foreign_customer_id,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                assert foreign_rows == []

                unknown_rows = list(
                    (
                        await db.execute(
                            select(Conversation).where(
                                Conversation.user_id == owner.id,
                                Conversation.customer_id == unknown_customer_id,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                assert unknown_rows == []

                valid_row = await db.scalar(
                    select(Conversation).where(
                        Conversation.id == valid_id,
                        Conversation.user_id == owner.id,
                        Conversation.customer_id == owner_customer_id,
                    )
                )

                assert valid_row is not None

                valid_ticket = await db.scalar(
                    select(Ticket).where(
                        Ticket.user_id == owner.id,
                        Ticket.conversation_id == valid_row.id,
                    )
                )

                assert valid_ticket is not None

    finally:
        app.dependency_overrides.clear()

        await _delete_conversation_chain(created_conversation_ids)

        customer_ids = [
            customer_id
            for customer_id in (
                owner_customer_id,
                foreign_customer_id,
            )
            if customer_id is not None
        ]

        if customer_ids:
            async with SessionLocal() as db:
                await db.execute(delete(Customer).where(Customer.id.in_(customer_ids)))
                await db.commit()


@pytest.mark.asyncio
async def test_foreign_customer_create_failure_has_no_ticket_side_effect():
    owner = FakeUser("conversation-owner-side-effect@example.com")
    foreign = FakeUser("conversation-foreign-side-effect@example.com")

    foreign_customer_id = None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            app.dependency_overrides[get_current_user] = lambda: foreign

            customer = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Foreign Customer",
                    "email": f"{uuid4().hex}@example.com",
                },
            )

            assert customer.status_code == 200
            foreign_customer_id = customer.json()["id"]

            async with SessionLocal() as db:
                before_conversations = list(
                    (
                        await db.execute(
                            select(Conversation.id).where(
                                Conversation.user_id == owner.id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                before_tickets = list(
                    (
                        await db.execute(
                            select(Ticket.id).where(Ticket.user_id == owner.id)
                        )
                    )
                    .scalars()
                    .all()
                )

            app.dependency_overrides[get_current_user] = lambda: owner

            response = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": foreign_customer_id,
                    "channel": "email",
                    "subject": "Must not persist",
                },
            )

            assert response.status_code == 404

            async with SessionLocal() as db:
                after_conversations = list(
                    (
                        await db.execute(
                            select(Conversation.id).where(
                                Conversation.user_id == owner.id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                after_tickets = list(
                    (
                        await db.execute(
                            select(Ticket.id).where(Ticket.user_id == owner.id)
                        )
                    )
                    .scalars()
                    .all()
                )

                assert after_conversations == before_conversations
                assert after_tickets == before_tickets

    finally:
        app.dependency_overrides.clear()

        if foreign_customer_id is not None:
            async with SessionLocal() as db:
                await db.execute(
                    delete(Customer).where(Customer.id == foreign_customer_id)
                )
                await db.commit()
