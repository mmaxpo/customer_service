from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    ConversationMessage,
)
from app.main import app


class FakeUser:
    def __init__(self, email: str):
        self.id = uuid4()
        self.email = email


@pytest.mark.asyncio
async def test_message_write_requires_conversation_ownership():
    owner = FakeUser("message-write-owner@example.com")
    foreign = FakeUser("message-write-foreign@example.com")

    owner_customer_id = None
    foreign_customer_id = None
    owner_conversation_id = None
    foreign_conversation_id = None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            app.dependency_overrides[get_current_user] = lambda: owner

            owner_customer = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Message Owner",
                    "email": f"{uuid4().hex}@example.com",
                },
            )

            assert owner_customer.status_code == 200
            owner_customer_id = owner_customer.json()["id"]

            owner_conversation = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": owner_customer_id,
                    "channel": "chat",
                    "subject": "Owner conversation",
                },
            )

            assert owner_conversation.status_code == 200
            owner_conversation_id = owner_conversation.json()["id"]

            own_write = await client.post(
                (f"/customer-service/conversations/{owner_conversation_id}/messages"),
                json={
                    "sender_type": "agent",
                    "body": "valid owner message",
                },
            )

            assert own_write.status_code == 200

            app.dependency_overrides[get_current_user] = lambda: foreign

            foreign_customer = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Foreign Message Owner",
                    "email": f"{uuid4().hex}@example.com",
                },
            )

            assert foreign_customer.status_code == 200
            foreign_customer_id = foreign_customer.json()["id"]

            foreign_conversation = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": foreign_customer_id,
                    "channel": "email",
                    "subject": "Foreign conversation",
                },
            )

            assert foreign_conversation.status_code == 200
            foreign_conversation_id = foreign_conversation.json()["id"]

            foreign_seed = await client.post(
                (f"/customer-service/conversations/{foreign_conversation_id}/messages"),
                json={
                    "sender_type": "customer",
                    "body": "foreign private message",
                },
            )

            assert foreign_seed.status_code == 200

            async with SessionLocal() as db:
                before_ids = list(
                    (
                        await db.execute(
                            select(ConversationMessage.id).where(
                                ConversationMessage.conversation_id
                                == foreign_conversation_id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

            app.dependency_overrides[get_current_user] = lambda: owner

            attack_body = "cross tenant message " + uuid4().hex

            attack = await client.post(
                (f"/customer-service/conversations/{foreign_conversation_id}/messages"),
                json={
                    "sender_type": "agent",
                    "body": attack_body,
                },
            )

            assert attack.status_code == 404
            assert attack.json() == {"detail": "Conversation not found"}

            async with SessionLocal() as db:
                after_ids = list(
                    (
                        await db.execute(
                            select(ConversationMessage.id).where(
                                ConversationMessage.conversation_id
                                == foreign_conversation_id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                injected = list(
                    (
                        await db.execute(
                            select(ConversationMessage.id).where(
                                ConversationMessage.conversation_id
                                == foreign_conversation_id,
                                ConversationMessage.body == attack_body,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

            assert after_ids == before_ids
            assert injected == []

            foreign_read = await client.get(
                (f"/customer-service/conversations/{foreign_conversation_id}/messages")
            )

            assert foreign_read.status_code == 404

            app.dependency_overrides[get_current_user] = lambda: foreign

            foreign_owner_read = await client.get(
                (f"/customer-service/conversations/{foreign_conversation_id}/messages")
            )

            assert foreign_owner_read.status_code == 200
            assert attack_body not in foreign_owner_read.text

    finally:
        app.dependency_overrides.clear()

        # Use the tested HTTP delete path so all conversation
        # dependency cleanup remains owned by production logic.
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            if owner_conversation_id is not None:
                app.dependency_overrides[get_current_user] = lambda: owner

                response = await client.delete(
                    (f"/customer-service/conversations/{owner_conversation_id}")
                )

                assert response.status_code in {
                    204,
                    404,
                }

            if foreign_conversation_id is not None:
                app.dependency_overrides[get_current_user] = lambda: foreign

                response = await client.delete(
                    (f"/customer-service/conversations/{foreign_conversation_id}")
                )

                assert response.status_code in {
                    204,
                    404,
                }

        app.dependency_overrides.clear()

        from sqlalchemy import delete

        from app.domains.customer_service.models import (
            Customer,
        )

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
