from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    ConversationMessage,
    CustomerServiceExternalConversationLink,
    CustomerServiceExternalMessageLink,
)
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "omnichannel-inbound-idempotency@example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize("channel", ["whatsapp", "instagram", "generic"])
async def test_duplicate_inbound_provider_message_is_idempotent(channel):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    external_account_id = f"{channel}-acct-{uuid4()}"
    external_thread_id = f"{channel}-thread-{uuid4()}"
    external_message_id = f"{channel}-message-{uuid4()}"

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "channel": channel,
                "external_account_id": external_account_id,
                "external_thread_id": external_thread_id,
                "external_message_id": external_message_id,
                "external_customer_id": f"{channel}-customer-{uuid4()}",
                "customer_name": "Duplicate Inbound Customer",
                "customer_email": f"{uuid4()}@example.com",
                "body": "Where is my order?",
                "meta": {"source": "duplicate-test"},
            }

            first = await client.post(
                "/customer-service/omnichannel/inbound",
                json=payload,
            )
            second = await client.post(
                "/customer-service/omnichannel/inbound",
                json=payload,
            )

            assert first.status_code == 200
            assert second.status_code == 200

            first_data = first.json()
            second_data = second.json()

            assert second_data["conversation_id"] == first_data["conversation_id"]
            assert second_data["message_id"] == first_data["message_id"]

            conversation_id = first_data["conversation_id"]
            message_id = first_data["message_id"]

        async with SessionLocal() as db:
            messages_result = await db.execute(
                select(ConversationMessage).where(
                    ConversationMessage.conversation_id == conversation_id,
                    ConversationMessage.body == payload["body"],
                )
            )
            messages = list(messages_result.scalars().all())

            assert len(messages) == 1
            assert str(messages[0].id) == message_id

            conversation_links_result = await db.execute(
                select(CustomerServiceExternalConversationLink).where(
                    CustomerServiceExternalConversationLink.user_id == user.id,
                    CustomerServiceExternalConversationLink.channel == channel,
                    CustomerServiceExternalConversationLink.external_account_id
                    == external_account_id,
                    CustomerServiceExternalConversationLink.external_thread_id
                    == external_thread_id,
                )
            )
            conversation_links = list(conversation_links_result.scalars().all())

            assert len(conversation_links) == 1
            assert str(conversation_links[0].conversation_id) == conversation_id

            message_links_result = await db.execute(
                select(CustomerServiceExternalMessageLink).where(
                    CustomerServiceExternalMessageLink.user_id == user.id,
                    CustomerServiceExternalMessageLink.channel == channel,
                    CustomerServiceExternalMessageLink.external_account_id
                    == external_account_id,
                    CustomerServiceExternalMessageLink.external_message_id
                    == external_message_id,
                )
            )
            message_links = list(message_links_result.scalars().all())

            assert len(message_links) == 1
            assert str(message_links[0].message_id) == message_id

    finally:
        app.dependency_overrides.pop(get_current_user, None)
