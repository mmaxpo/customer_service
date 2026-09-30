from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    ConversationMessage,
    Customer,
)
from app.domains.customer_service.schemas.conversations import (
    ConversationMessageCreate,
    SenderType,
)
from app.main import app


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "source-identity@example.com"


def test_message_schema_requires_complete_source_identity():
    with pytest.raises(
        ValueError,
        match=("source_type and source_message_id must be provided together"),
    ):
        ConversationMessageCreate(
            sender_type=SenderType.AGENT,
            body="partial",
            source_type="provider",
        )

    with pytest.raises(
        ValueError,
        match=("source_type and source_message_id must be provided together"),
    ):
        ConversationMessageCreate(
            sender_type=SenderType.AGENT,
            body="partial",
            source_message_id=uuid4(),
        )

    with pytest.raises(
        ValueError,
        match=("source_type and source_message_id must be provided together"),
    ):
        ConversationMessageCreate(
            sender_type=SenderType.AGENT,
            body="blank",
            source_type="   ",
            source_message_id=uuid4(),
        )


def test_message_schema_normalizes_source_type():
    source_message_id = uuid4()

    message = ConversationMessageCreate(
        sender_type=SenderType.AGENT,
        body="normalized",
        source_type="  provider-event  ",
        source_message_id=source_message_id,
    )

    assert message.source_type == "provider-event"
    assert message.source_message_id == source_message_id


@pytest.mark.asyncio
async def test_message_http_rejects_partial_source_identity_with_422():
    user = FakeUser()
    customer_id = None
    conversation_id = None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            app.dependency_overrides[get_current_user] = lambda: user

            customer = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Source Identity Customer",
                    "email": f"{uuid4().hex}@example.com",
                },
            )

            assert customer.status_code == 200
            customer_id = customer.json()["id"]

            conversation = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": customer_id,
                    "channel": "email",
                    "subject": "Source identity validation",
                },
            )

            assert conversation.status_code == 200
            conversation_id = conversation.json()["id"]

            endpoint = f"/customer-service/conversations/{conversation_id}/messages"

            cases = (
                {
                    "sender_type": "agent",
                    "body": "source type only",
                    "source_type": "provider",
                },
                {
                    "sender_type": "agent",
                    "body": "source id only",
                    "source_message_id": str(uuid4()),
                },
                {
                    "sender_type": "agent",
                    "body": "blank source",
                    "source_type": "   ",
                    "source_message_id": str(uuid4()),
                },
            )

            for payload in cases:
                response = await client.post(
                    endpoint,
                    json=payload,
                )

                assert response.status_code == 422
                assert (
                    "source_type and source_message_id "
                    "must be provided together" in response.text
                )

            async with SessionLocal() as db:
                malformed_count = len(
                    list(
                        (
                            await db.execute(
                                select(ConversationMessage.id).where(
                                    ConversationMessage.conversation_id
                                    == conversation_id
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                )

            assert malformed_count == 0

    finally:
        app.dependency_overrides.clear()

        if conversation_id is not None:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                app.dependency_overrides[get_current_user] = lambda: user

                response = await client.delete(
                    (f"/customer-service/conversations/{conversation_id}")
                )

                assert response.status_code in {
                    204,
                    404,
                }

        app.dependency_overrides.clear()

        if customer_id is not None:
            async with SessionLocal() as db:
                await db.execute(delete(Customer).where(Customer.id == customer_id))
                await db.commit()


@pytest.mark.asyncio
async def test_source_identified_message_retry_remains_idempotent():
    user = FakeUser()
    customer_id = None
    conversation_id = None
    source_message_id = uuid4()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            app.dependency_overrides[get_current_user] = lambda: user

            customer = await client.post(
                "/customer-service/customers/",
                json={
                    "name": "Idempotent Source Customer",
                    "email": f"{uuid4().hex}@example.com",
                },
            )

            assert customer.status_code == 200
            customer_id = customer.json()["id"]

            conversation = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": customer_id,
                    "channel": "email",
                    "subject": "Source identity retry",
                },
            )

            assert conversation.status_code == 200
            conversation_id = conversation.json()["id"]

            endpoint = f"/customer-service/conversations/{conversation_id}/messages"

            payload = {
                "sender_type": "agent",
                "body": "durable source message",
                "source_type": " provider-event ",
                "source_message_id": str(source_message_id),
            }

            first = await client.post(
                endpoint,
                json=payload,
            )
            retry = await client.post(
                endpoint,
                json=payload,
            )

            assert first.status_code == 200
            assert retry.status_code == 200

            assert first.json()["id"] == retry.json()["id"]
            assert first.json()["source_type"] == "provider-event"
            assert retry.json()["source_type"] == "provider-event"

            async with SessionLocal() as db:
                rows = list(
                    (
                        await db.execute(
                            select(ConversationMessage).where(
                                ConversationMessage.conversation_id == conversation_id,
                                ConversationMessage.source_type == "provider-event",
                                ConversationMessage.source_message_id
                                == source_message_id,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

            assert len(rows) == 1

    finally:
        app.dependency_overrides.clear()

        if conversation_id is not None:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                app.dependency_overrides[get_current_user] = lambda: user

                response = await client.delete(
                    (f"/customer-service/conversations/{conversation_id}")
                )

                assert response.status_code in {
                    204,
                    404,
                }

        app.dependency_overrides.clear()

        if customer_id is not None:
            async with SessionLocal() as db:
                await db.execute(delete(Customer).where(Customer.id == customer_id))
                await db.commit()
