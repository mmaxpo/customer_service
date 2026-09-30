from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    CustomerServiceExternalConversationLink,
)
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "omnichannel-conversation-linking@example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize("channel", ["whatsapp", "instagram", "generic"])
async def test_same_external_thread_reuses_same_canonical_conversation(channel):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    external_account_id = f"{channel}-acct-{uuid4()}"
    external_thread_id = f"{channel}-thread-{uuid4()}"
    external_customer_id = f"{channel}-customer-{uuid4()}"

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": channel,
                    "external_account_id": external_account_id,
                    "external_thread_id": external_thread_id,
                    "external_message_id": f"{channel}-msg-1-{uuid4()}",
                    "external_customer_id": external_customer_id,
                    "customer_name": "Same Thread Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "First message",
                },
            )
            second = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": channel,
                    "external_account_id": external_account_id,
                    "external_thread_id": external_thread_id,
                    "external_message_id": f"{channel}-msg-2-{uuid4()}",
                    "external_customer_id": external_customer_id,
                    "customer_name": "Same Thread Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Second message",
                },
            )

            assert first.status_code == 200
            assert second.status_code == 200

            first_data = first.json()
            second_data = second.json()

            assert second_data["conversation_id"] == first_data["conversation_id"]
            assert second_data["message_id"] != first_data["message_id"]

            conversation_id = first_data["conversation_id"]

        async with SessionLocal() as db:
            result = await db.execute(
                select(CustomerServiceExternalConversationLink).where(
                    CustomerServiceExternalConversationLink.user_id == user.id,
                    CustomerServiceExternalConversationLink.channel == channel,
                    CustomerServiceExternalConversationLink.external_account_id
                    == external_account_id,
                    CustomerServiceExternalConversationLink.external_thread_id
                    == external_thread_id,
                )
            )
            links = list(result.scalars().all())

            assert len(links) == 1
            assert str(links[0].conversation_id) == conversation_id

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_different_external_threads_create_different_canonical_conversations():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    channel = "whatsapp"
    external_account_id = f"{channel}-acct-{uuid4()}"
    external_customer_id = f"{channel}-customer-{uuid4()}"

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": channel,
                    "external_account_id": external_account_id,
                    "external_thread_id": f"{channel}-thread-a-{uuid4()}",
                    "external_message_id": f"{channel}-msg-a-{uuid4()}",
                    "external_customer_id": external_customer_id,
                    "customer_name": "Thread A Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Thread A message",
                },
            )
            second = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": channel,
                    "external_account_id": external_account_id,
                    "external_thread_id": f"{channel}-thread-b-{uuid4()}",
                    "external_message_id": f"{channel}-msg-b-{uuid4()}",
                    "external_customer_id": external_customer_id,
                    "customer_name": "Thread B Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Thread B message",
                },
            )

            assert first.status_code == 200
            assert second.status_code == 200
            assert second.json()["conversation_id"] != first.json()["conversation_id"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)
