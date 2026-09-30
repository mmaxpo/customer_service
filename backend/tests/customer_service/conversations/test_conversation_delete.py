from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "delete-conversation@example.com"


async def _create_customer(client):
    response = await client.post(
        "/customer-service/customers/",
        json={
            "name": "Delete Test Customer",
            "email": f"{uuid4()}@example.com",
            "phone": None,
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


async def _create_conversation(client, *, customer_id):
    response = await client.post(
        "/customer-service/conversations/",
        json={
            "customer_id": customer_id,
            "channel": "website",
            "subject": "Delete me",
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


@pytest.mark.asyncio
async def test_delete_conversation_removes_it_from_inbox():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            customer = await _create_customer(client)
            conversation = await _create_conversation(
                client,
                customer_id=customer["id"],
            )

            delete_response = await client.delete(
                f"/customer-service/conversations/{conversation['id']}"
            )

            assert delete_response.status_code == 204

            detail_response = await client.get(
                f"/customer-service/conversations/{conversation['id']}"
            )
            assert detail_response.status_code == 404

            inbox_response = await client.get("/customer-service/inbox/")
            assert inbox_response.status_code == 200

            conversation_ids = {
                item["conversation_id"] for item in inbox_response.json()
            }
            assert conversation["id"] not in conversation_ids

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_delete_missing_conversation_returns_404():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete(
                "/customer-service/conversations/00000000-0000-0000-0000-000000000000"
            )

            assert response.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)
