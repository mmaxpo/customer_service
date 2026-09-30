from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import get_db
from app.domains.customer_service.inbox.schemas import (
    InboxEmailAddress,
    NormalizedInboundEmail,
)
from app.domains.customer_service.inbox.service import InboundEmailIngestService
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "inbox@test.com"


@pytest.mark.asyncio
async def test_inbound_email_creates_and_threads_conversation():
    user = FakeUser()

    async for db in get_db():
        service = InboundEmailIngestService(db)

        external_thread_id = f"thread-{uuid4()}"

        first = await service.ingest(
            user_id=user.id,
            email=NormalizedInboundEmail(
                provider="test",
                external_account_id="support@example.com",
                external_message_id=f"msg-{uuid4()}",
                external_thread_id=external_thread_id,
                from_address=InboxEmailAddress(
                    email="customer@example.com",
                    name="Customer One",
                ),
                to=[
                    InboxEmailAddress(
                        email="support@example.com",
                        name="Support",
                    )
                ],
                subject="Where is my order?",
                body_text="My order has not arrived.",
            ),
        )

        second = await service.ingest(
            user_id=user.id,
            email=NormalizedInboundEmail(
                provider="test",
                external_account_id="support@example.com",
                external_message_id=f"msg-{uuid4()}",
                external_thread_id=external_thread_id,
                from_address=InboxEmailAddress(
                    email="customer@example.com",
                    name="Customer One",
                ),
                subject="Re: Where is my order?",
                body_text="Any update?",
            ),
        )

        assert first.created_conversation is True
        assert second.created_conversation is False
        assert second.conversation_id == first.conversation_id
        assert second.customer_email == "customer@example.com"

        break


@pytest.mark.asyncio
async def test_inbound_email_endpoint_ingests_message():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/customer-service/inbox/email/ingest",
                json={
                    "provider": "test",
                    "external_account_id": "support@example.com",
                    "external_message_id": f"msg-{uuid4()}",
                    "external_thread_id": f"thread-{uuid4()}",
                    "from_address": {
                        "email": "buyer@example.com",
                        "name": "Buyer",
                    },
                    "to": [
                        {
                            "email": "support@example.com",
                            "name": "Support",
                        }
                    ],
                    "subject": "Refund request",
                    "body_text": "I need a refund.",
                },
            )

            assert response.status_code == 200, response.text
            body = response.json()

            assert body["created_conversation"] is True
            assert body["customer_email"] == "buyer@example.com"
            assert body["provider"] == "test"

    finally:
        app.dependency_overrides.clear()
