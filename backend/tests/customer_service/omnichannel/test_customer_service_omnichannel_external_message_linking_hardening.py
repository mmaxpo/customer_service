from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.models import (
    CustomerServiceExternalMessageLink,
)
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "external-message-linking@example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize("channel", ["whatsapp", "instagram", "generic"])
async def test_duplicate_external_message_id_returns_same_internal_message(channel):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    external_account_id = f"{channel}-acct-{uuid4()}"
    external_thread_id = f"{channel}-thread-{uuid4()}"
    external_message_id = f"{channel}-message-{uuid4()}"

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            payload = {
                "channel": channel,
                "external_account_id": external_account_id,
                "external_thread_id": external_thread_id,
                "external_message_id": external_message_id,
                "external_customer_id": f"{channel}-customer-{uuid4()}",
                "customer_name": "External Message Customer",
                "customer_email": f"{uuid4()}@example.com",
                "body": "Where is my order?",
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

            assert first_data["message_id"] == second_data["message_id"]

            message_id = first_data["message_id"]

        async with SessionLocal() as db:
            result = await db.execute(
                select(CustomerServiceExternalMessageLink).where(
                    CustomerServiceExternalMessageLink.user_id == user.id,
                    CustomerServiceExternalMessageLink.channel == channel,
                    CustomerServiceExternalMessageLink.external_account_id
                    == external_account_id,
                    CustomerServiceExternalMessageLink.external_message_id
                    == external_message_id,
                )
            )

            links = list(result.scalars().all())

            assert len(links) == 1
            assert str(links[0].message_id) == message_id

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("channel", ["whatsapp", "instagram", "generic"])
async def test_different_external_message_ids_create_different_internal_messages(
    channel,
):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            common = {
                "channel": channel,
                "external_account_id": f"{channel}-acct-{uuid4()}",
                "external_thread_id": f"{channel}-thread-{uuid4()}",
                "external_customer_id": f"{channel}-customer-{uuid4()}",
                "customer_name": "Different Message Customer",
                "customer_email": f"{uuid4()}@example.com",
            }

            first = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    **common,
                    "external_message_id": f"{channel}-msg-1-{uuid4()}",
                    "body": "Message One",
                },
            )

            second = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    **common,
                    "external_message_id": f"{channel}-msg-2-{uuid4()}",
                    "body": "Message Two",
                },
            )

            assert first.status_code == 200
            assert second.status_code == 200

            assert first.json()["message_id"] != second.json()["message_id"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)
