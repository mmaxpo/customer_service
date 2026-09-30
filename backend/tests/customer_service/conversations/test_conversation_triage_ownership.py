from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    Conversation,
    ConversationTag,
    Customer,
    CustomerServiceAuditLog,
    Ticket,
)
from app.main import app


class FakeUser:
    def __init__(self, email: str):
        self.id = uuid4()
        self.email = email


async def _delete_customer(customer_id):
    async with SessionLocal() as db:
        customer = await db.get(
            Customer,
            UUID(str(customer_id)),
        )

        if customer is not None:
            await db.delete(customer)
            await db.commit()


async def _delete_conversation(user, conversation_id):
    app.dependency_overrides[get_current_user] = lambda u=user: u

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.delete(
            f"/customer-service/conversations/{conversation_id}"
        )

    assert response.status_code in {204, 404}


@pytest.mark.asyncio
async def test_foreign_conversation_triage_is_rejected_without_side_effects():
    owner = FakeUser("triage-owner@example.com")
    attacker = FakeUser("triage-attacker@example.com")

    customer_id = None
    conversation_id = None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            app.dependency_overrides[get_current_user] = lambda: owner

            customer = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Triage Owner",
                    "email": (f"{uuid4().hex}@example.com"),
                },
            )

            assert customer.status_code == 200
            customer_id = customer.json()["id"]

            conversation = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": customer_id,
                    "channel": "email",
                    "subject": "Triage ownership",
                },
            )

            assert conversation.status_code == 200
            conversation_id = conversation.json()["id"]

            async with SessionLocal() as db:
                ticket = await db.scalar(
                    select(Ticket).where(
                        Ticket.conversation_id == UUID(conversation_id)
                    )
                )

                before_priority = ticket.priority if ticket is not None else None

                before_tags = set(
                    (
                        await db.scalars(
                            select(ConversationTag.id).where(
                                ConversationTag.conversation_id == UUID(conversation_id)
                            )
                        )
                    ).all()
                )

                before_audits = set(
                    (
                        await db.scalars(
                            select(CustomerServiceAuditLog.id).where(
                                CustomerServiceAuditLog.entity_type == "conversation",
                                CustomerServiceAuditLog.entity_id
                                == UUID(conversation_id),
                            )
                        )
                    ).all()
                )

            app.dependency_overrides[get_current_user] = lambda: attacker

            attack = await client.post(
                (f"/customer-service/conversations/{conversation_id}/triage"),
                json={"message": ("urgent refund damaged package")},
            )

            assert attack.status_code == 404
            assert attack.json() == {"detail": "Conversation not found"}

            async with SessionLocal() as db:
                persisted = await db.get(
                    Conversation,
                    UUID(conversation_id),
                )

                assert persisted is not None
                assert persisted.user_id == owner.id

                ticket = await db.scalar(
                    select(Ticket).where(
                        Ticket.conversation_id == UUID(conversation_id)
                    )
                )

                after_priority = ticket.priority if ticket is not None else None

                after_tags = set(
                    (
                        await db.scalars(
                            select(ConversationTag.id).where(
                                ConversationTag.conversation_id == UUID(conversation_id)
                            )
                        )
                    ).all()
                )

                after_audits = set(
                    (
                        await db.scalars(
                            select(CustomerServiceAuditLog.id).where(
                                CustomerServiceAuditLog.entity_type == "conversation",
                                CustomerServiceAuditLog.entity_id
                                == UUID(conversation_id),
                            )
                        )
                    ).all()
                )

            assert after_priority == before_priority
            assert after_tags == before_tags
            assert after_audits == before_audits

    finally:
        app.dependency_overrides.clear()

        if conversation_id is not None:
            await _delete_conversation(
                owner,
                conversation_id,
            )

        app.dependency_overrides.clear()

        if customer_id is not None:
            await _delete_customer(customer_id)


@pytest.mark.asyncio
async def test_triage_requires_message_request_field():
    user = FakeUser("triage-validation@example.com")

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                (f"/customer-service/conversations/{uuid4()}/triage"),
                json={},
            )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()
