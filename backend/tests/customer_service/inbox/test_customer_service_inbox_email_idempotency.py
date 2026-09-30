from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    Customer,
)
from app.main import app


class FakeUser:
    def __init__(self, email: str):
        self.id = uuid4()
        self.email = email


def inbound_payload(
    *,
    account_id: str,
    external_message_id: str,
    external_thread_id: str,
    customer_email: str,
):
    return {
        "provider": "email-idempotency-test",
        "external_account_id": account_id,
        "external_message_id": external_message_id,
        "external_thread_id": external_thread_id,
        "from_address": {
            "email": customer_email,
            "name": "Idempotency Buyer",
        },
        "to": [
            {
                "email": account_id,
                "name": "Support",
            }
        ],
        "subject": "Idempotency test",
        "body_text": "One provider delivery.",
    }


async def delete_created_conversation(
    *,
    user,
    conversation_id: str,
):
    app.dependency_overrides[get_current_user] = lambda: user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.delete(
            f"/customer-service/conversations/{conversation_id}"
        )

        assert response.status_code in {204, 404}


async def delete_customer(customer_id):
    async with SessionLocal() as db:
        customer = await db.get(
            Customer,
            UUID(str(customer_id)),
        )

        if customer is not None:
            await db.delete(customer)
            await db.commit()


async def conversation_state(conversation_id: str):
    async with SessionLocal() as db:
        conversation = await db.get(
            Conversation,
            UUID(conversation_id),
        )

        assert conversation is not None

        message_count = await db.scalar(
            select(func.count(ConversationMessage.id)).where(
                ConversationMessage.conversation_id == conversation.id
            )
        )

        return conversation, int(message_count or 0)


@pytest.mark.asyncio
async def test_sequential_duplicate_email_returns_original_message_once():
    user = FakeUser("email-idempotency-sequential@example.com")

    app.dependency_overrides[get_current_user] = lambda: user

    conversation_id = None
    customer_id = None

    try:
        payload = inbound_payload(
            account_id="support-a@example.com",
            external_message_id=f"message-{uuid4()}",
            external_thread_id=f"thread-{uuid4()}",
            customer_email=f"{uuid4().hex}@example.com",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.post(
                "/customer-service/inbox/email/ingest",
                json=payload,
            )
            second = await client.post(
                "/customer-service/inbox/email/ingest",
                json=payload,
            )

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text

        first_data = first.json()
        second_data = second.json()

        conversation_id = first_data["conversation_id"]

        assert second_data["conversation_id"] == conversation_id
        assert second_data["message_id"] == first_data["message_id"]
        assert second_data["created_conversation"] is False

        conversation, count = await conversation_state(conversation_id)

        customer_id = conversation.customer_id

        assert count == 1

    finally:
        app.dependency_overrides.clear()

        if conversation_id is not None:
            await delete_created_conversation(
                user=user,
                conversation_id=conversation_id,
            )

        if customer_id is not None:
            await delete_customer(customer_id)

        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_concurrent_duplicate_email_creates_one_message():
    user = FakeUser("email-idempotency-concurrent@example.com")

    app.dependency_overrides[get_current_user] = lambda: user

    conversation_id = None
    customer_id = None

    try:
        payload = inbound_payload(
            account_id="support-concurrent@example.com",
            external_message_id=f"message-{uuid4()}",
            external_thread_id=f"thread-{uuid4()}",
            customer_email=f"{uuid4().hex}@example.com",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first, second = await asyncio.gather(
                client.post(
                    "/customer-service/inbox/email/ingest",
                    json=payload,
                ),
                client.post(
                    "/customer-service/inbox/email/ingest",
                    json=payload,
                ),
            )

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text

        first_data = first.json()
        second_data = second.json()

        assert first_data["conversation_id"] == second_data["conversation_id"]
        assert first_data["message_id"] == second_data["message_id"]

        conversation_id = first_data["conversation_id"]

        conversation, count = await conversation_state(conversation_id)

        customer_id = conversation.customer_id

        assert count == 1

    finally:
        app.dependency_overrides.clear()

        if conversation_id is not None:
            await delete_created_conversation(
                user=user,
                conversation_id=conversation_id,
            )

        if customer_id is not None:
            await delete_customer(customer_id)

        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_same_external_message_id_isolated_by_email_account():
    user = FakeUser("email-idempotency-account@example.com")

    app.dependency_overrides[get_current_user] = lambda: user

    conversation_ids = []
    customer_ids = set()

    try:
        external_message_id = f"shared-message-{uuid4()}"

        first_payload = inbound_payload(
            account_id="support-one@example.com",
            external_message_id=external_message_id,
            external_thread_id=f"thread-one-{uuid4()}",
            customer_email=f"{uuid4().hex}@example.com",
        )

        second_payload = inbound_payload(
            account_id="support-two@example.com",
            external_message_id=external_message_id,
            external_thread_id=f"thread-two-{uuid4()}",
            customer_email=f"{uuid4().hex}@example.com",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.post(
                "/customer-service/inbox/email/ingest",
                json=first_payload,
            )
            second = await client.post(
                "/customer-service/inbox/email/ingest",
                json=second_payload,
            )

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text

        first_data = first.json()
        second_data = second.json()

        assert first_data["message_id"] != second_data["message_id"]
        assert first_data["conversation_id"] != second_data["conversation_id"]

        conversation_ids.extend(
            [
                first_data["conversation_id"],
                second_data["conversation_id"],
            ]
        )

        for conversation_id in conversation_ids:
            conversation, count = await conversation_state(conversation_id)

            customer_ids.add(conversation.customer_id)

            assert count == 1

    finally:
        app.dependency_overrides.clear()

        for conversation_id in conversation_ids:
            await delete_created_conversation(
                user=user,
                conversation_id=conversation_id,
            )

        for customer_id in customer_ids:
            await delete_customer(customer_id)

        app.dependency_overrides.clear()
