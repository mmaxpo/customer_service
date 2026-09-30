from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    Conversation,
    Customer,
    CustomerChatInboxLink,
    CustomerChatMessage,
    CustomerChatSession,
    CustomerIdentity,
    Ticket,
)
from app.main import app


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "chat-identity@example.com"


async def _cleanup(*, user_id):
    async with SessionLocal() as db:
        links = list(
            (
                await db.scalars(
                    select(CustomerChatInboxLink).where(
                        CustomerChatInboxLink.user_id == user_id
                    )
                )
            ).all()
        )

        conversation_ids = [row.conversation_id for row in links]

        session_ids = [row.chat_session_id for row in links]

        if conversation_ids:
            await db.execute(
                delete(Ticket).where(Ticket.conversation_id.in_(conversation_ids))
            )

            await db.execute(
                delete(CustomerChatInboxLink).where(
                    CustomerChatInboxLink.conversation_id.in_(conversation_ids)
                )
            )

            await db.execute(
                delete(Conversation).where(Conversation.id.in_(conversation_ids))
            )

        if session_ids:
            await db.execute(
                delete(CustomerChatMessage).where(
                    CustomerChatMessage.session_id.in_(session_ids)
                )
            )

            await db.execute(
                delete(CustomerChatSession).where(
                    CustomerChatSession.id.in_(session_ids)
                )
            )

        await db.execute(delete(Customer).where(Customer.user_id == user_id))

        await db.commit()


@pytest.mark.asyncio
async def test_same_website_visitor_reuses_customer_across_sessions():
    user = FakeUser()
    visitor_id = f"visitor-{uuid4()}"

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings = await client.get("/customer-service/chat/widget/settings")

            assert settings.status_code == 200

            public_key = settings.json()["public_key"]

            first = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": visitor_id,
                    "channel": "website",
                },
            )

            second = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": visitor_id,
                    "channel": "website",
                },
            )

            assert first.status_code == 200, first.text
            assert second.status_code == 200, second.text

            async with SessionLocal() as db:
                first_link = await db.scalar(
                    select(CustomerChatInboxLink).where(
                        CustomerChatInboxLink.chat_session_id
                        == UUID(first.json()["id"])
                    )
                )

                second_link = await db.scalar(
                    select(CustomerChatInboxLink).where(
                        CustomerChatInboxLink.chat_session_id
                        == UUID(second.json()["id"])
                    )
                )

                assert first_link is not None
                assert second_link is not None

                assert first_link.customer_id == second_link.customer_id

                visitor_identity_count = await db.scalar(
                    select(func.count(CustomerIdentity.id)).where(
                        CustomerIdentity.user_id == user.id,
                        CustomerIdentity.customer_id == first_link.customer_id,
                        CustomerIdentity.identity_type == "website_visitor",
                        CustomerIdentity.namespace == f"website:{user.id}",
                        CustomerIdentity.normalized_value == visitor_id,
                    )
                )

                assert visitor_identity_count == 1

    finally:
        app.dependency_overrides.clear()
        await _cleanup(user_id=user.id)


@pytest.mark.asyncio
async def test_website_chat_email_converges_with_existing_customer():
    user = FakeUser()

    customer_email = f"chat-existing-{uuid4().hex}@example.com"

    existing_customer_id = None

    async with SessionLocal() as db:
        existing = Customer(
            user_id=user.id,
            workspace_id=None,
            name="Existing Customer",
            email=customer_email,
        )

        db.add(existing)
        await db.commit()
        await db.refresh(existing)

        existing_customer_id = existing.id

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings = await client.get("/customer-service/chat/widget/settings")

            assert settings.status_code == 200

            public_key = settings.json()["public_key"]

            session = await client.post(
                f"/customer-service/chat/public/{public_key}/sessions",
                json={
                    "visitor_id": (f"visitor-{uuid4()}"),
                    "channel": "website",
                    "customer_email": (customer_email.upper()),
                    "customer_name": ("Existing Customer"),
                },
            )

            assert session.status_code == 200, session.text

            async with SessionLocal() as db:
                link = await db.scalar(
                    select(CustomerChatInboxLink).where(
                        CustomerChatInboxLink.chat_session_id
                        == UUID(session.json()["id"])
                    )
                )

                assert link is not None

                assert link.customer_id == existing_customer_id

                identities = list(
                    (
                        await db.scalars(
                            select(CustomerIdentity).where(
                                CustomerIdentity.customer_id == existing_customer_id
                            )
                        )
                    ).all()
                )

                identity_types = {row.identity_type for row in identities}

                assert "email" in identity_types
                assert "website_visitor" in identity_types

    finally:
        app.dependency_overrides.clear()
        await _cleanup(user_id=user.id)
