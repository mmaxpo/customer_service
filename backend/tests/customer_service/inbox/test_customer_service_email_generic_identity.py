from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from app.core.session import SessionLocal
from app.domains.customer_service.inbox.schemas import (
    InboxEmailAddress,
    NormalizedInboundEmail,
)
from app.domains.customer_service.inbox.service import (
    InboundEmailIngestService,
)
from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    Customer,
    CustomerIdentity,
    CustomerServiceExternalMessageLink,
    Ticket,
)


@pytest.mark.asyncio
async def test_inbound_email_adopts_pre_registry_customer():
    user_id = uuid4()
    email_address = f"legacy-email-{uuid4().hex}@example.com"

    customer_id = None
    conversation_id = None

    try:
        async with SessionLocal() as db:
            legacy = Customer(
                user_id=user_id,
                workspace_id=None,
                name="Legacy Email Customer",
                email=email_address,
            )

            db.add(legacy)
            await db.commit()
            await db.refresh(legacy)

            customer_id = legacy.id

        async with SessionLocal() as db:
            result = await InboundEmailIngestService(db).ingest(
                user_id=user_id,
                email=NormalizedInboundEmail(
                    provider="identity-adoption-test",
                    external_account_id=("support@example.com"),
                    external_message_id=(f"message-{uuid4()}"),
                    external_thread_id=(f"thread-{uuid4()}"),
                    from_address=InboxEmailAddress(
                        email=email_address.upper(),
                        name="Legacy Email Customer",
                    ),
                    subject="Legacy adoption",
                    body_text="Hello",
                ),
            )

            conversation_id = result.conversation_id

        async with SessionLocal() as db:
            conversation = await db.scalar(
                select(Conversation).where(Conversation.id == conversation_id)
            )

            assert conversation is not None
            assert conversation.customer_id == customer_id

            customer_count = await db.scalar(
                select(func.count(Customer.id)).where(
                    Customer.user_id == user_id,
                    func.lower(Customer.email) == email_address,
                )
            )

            assert customer_count == 1

            identity_count = await db.scalar(
                select(func.count(CustomerIdentity.id)).where(
                    CustomerIdentity.user_id == user_id,
                    CustomerIdentity.customer_id == customer_id,
                    CustomerIdentity.identity_type == "email",
                    CustomerIdentity.namespace == "global",
                    CustomerIdentity.normalized_value == email_address,
                )
            )

            assert identity_count == 1

    finally:
        async with SessionLocal() as db:
            if conversation_id is not None:
                # External message links reference both the
                # canonical ConversationMessage and Conversation.
                # Remove them before either parent row.
                await db.execute(
                    delete(CustomerServiceExternalMessageLink).where(
                        CustomerServiceExternalMessageLink.conversation_id
                        == conversation_id
                    )
                )

                await db.execute(
                    delete(Ticket).where(Ticket.conversation_id == conversation_id)
                )

                await db.execute(
                    delete(ConversationMessage).where(
                        ConversationMessage.conversation_id == conversation_id
                    )
                )

                await db.execute(
                    delete(Conversation).where(Conversation.id == conversation_id)
                )

            if customer_id is not None:
                await db.execute(delete(Customer).where(Customer.id == customer_id))

            await db.commit()
