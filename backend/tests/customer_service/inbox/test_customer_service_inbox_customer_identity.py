from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select, text

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    CustomerServiceExternalMessageLink,
    Customer,
    Ticket,
)
from app.main import app


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "inbox-customer-identity@example.com"


@pytest.mark.asyncio
async def test_concurrent_inbound_messages_share_one_customer_identity():
    user = FakeUser()

    customer_email = f"inbound-race-{uuid4().hex}@example.com"

    customer_ids = []
    conversation_ids = []

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first_payload = {
                "provider": "identity-concurrency-test",
                "external_account_id": "support@example.com",
                "external_message_id": f"msg-a-{uuid4()}",
                "external_thread_id": f"thread-a-{uuid4()}",
                "from_address": {
                    "email": customer_email,
                    "name": "Concurrent Buyer",
                },
                "subject": "First identity message",
                "body_text": "First message",
            }

            second_payload = {
                "provider": "identity-concurrency-test",
                "external_account_id": "support@example.com",
                "external_message_id": f"msg-b-{uuid4()}",
                "external_thread_id": f"thread-b-{uuid4()}",
                "from_address": {
                    "email": customer_email.upper(),
                    "name": "Concurrent Buyer",
                },
                "subject": "Second identity message",
                "body_text": "Second message",
            }

            first, second = await asyncio.gather(
                client.post(
                    "/customer-service/inbox/email/ingest",
                    json=first_payload,
                ),
                client.post(
                    "/customer-service/inbox/email/ingest",
                    json=second_payload,
                ),
            )

            assert first.status_code == 200, first.text
            assert second.status_code == 200, second.text

            conversation_ids.extend(
                [
                    first.json()["conversation_id"],
                    second.json()["conversation_id"],
                ]
            )

            async with SessionLocal() as db:
                customers = list(
                    (
                        await db.execute(
                            select(Customer).where(
                                Customer.user_id == user.id,
                                func.lower(Customer.email) == customer_email.lower(),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                customer_ids.extend(customer.id for customer in customers)

                assert len(customers) == 1
                assert customers[0].email == customer_email.lower()

                conversations = list(
                    (
                        await db.execute(
                            select(Conversation).where(
                                Conversation.id.in_(conversation_ids)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                assert len(conversations) == 2

                used_customer_ids = {
                    conversation.customer_id for conversation in conversations
                }

                assert used_customer_ids == {customers[0].id}

                identity_count = await db.scalar(
                    text(
                        """
                        SELECT count(*)
                        FROM cs_customer_identities
                        WHERE user_id = :user_id
                          AND customer_id = :customer_id
                          AND identity_type = 'email'
                          AND namespace = 'global'
                          AND normalized_value = :email
                        """
                    ),
                    {
                        "user_id": user.id,
                        "customer_id": customers[0].id,
                        "email": customer_email.lower(),
                    },
                )

                assert identity_count == 1

    finally:
        app.dependency_overrides.clear()

        async with SessionLocal() as db:
            if conversation_ids:
                await db.execute(
                    delete(Ticket).where(Ticket.conversation_id.in_(conversation_ids))
                )

                await db.execute(
                    delete(CustomerServiceExternalMessageLink).where(
                        CustomerServiceExternalMessageLink.conversation_id.in_(
                            conversation_ids
                        )
                    )
                )

                await db.execute(
                    delete(ConversationMessage).where(
                        ConversationMessage.conversation_id.in_(conversation_ids)
                    )
                )

                await db.execute(
                    delete(Conversation).where(Conversation.id.in_(conversation_ids))
                )

            if customer_ids:
                await db.execute(delete(Customer).where(Customer.id.in_(customer_ids)))

            await db.commit()
