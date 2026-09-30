from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    id = "11111111-1111-1111-1111-111111111111"
    email = "owner@example.com"


@pytest.mark.asyncio
async def test_conversation_messages_are_paginated_in_stable_order():
    app.dependency_overrides[get_current_user] = lambda: FakeUser()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Paginated Customer",
                        "email": f"page-{uuid4().hex}@example.com",
                    },
                )
            ).json()

            conversation = (
                await client.post(
                    "/customer-service/conversations/",
                    json={
                        "customer_id": customer["id"],
                        "channel": "email",
                        "subject": "Pagination",
                    },
                )
            ).json()

            for index in range(5):
                response = await client.post(
                    f"/customer-service/conversations/{conversation['id']}/messages",
                    json={
                        "sender_type": "customer",
                        "body": f"message-{index}",
                    },
                )
                assert response.status_code == 200

            page = await client.get(
                f"/customer-service/conversations/{conversation['id']}/messages",
                params={"limit": 2, "offset": 1},
            )

            assert page.status_code == 200
            bodies = [row["body"] for row in page.json()]

            assert bodies == ["message-1", "message-2"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_conversation_messages_returns_404_for_other_user_conversation():
    app.dependency_overrides[get_current_user] = lambda: FakeUser()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            missing = await client.get(
                "/customer-service/conversations/00000000-0000-0000-0000-000000000001/messages"
            )

            assert missing.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)
