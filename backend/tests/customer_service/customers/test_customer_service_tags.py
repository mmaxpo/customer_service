from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "tags@example.com"


@pytest.mark.asyncio
async def test_conversation_tags_add_list_remove():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Tag Customer",
                        "email": f"{uuid4()}@example.com",
                        "phone": "+49123456789",
                    },
                )
            ).json()

            conversation = (
                await client.post(
                    "/customer-service/conversations/",
                    json={
                        "customer_id": customer["id"],
                        "channel": "email",
                        "subject": "Tag issue",
                    },
                )
            ).json()

            add_res = await client.post(
                f"/customer-service/conversations/{conversation['id']}/tags/",
                json={"name": " Refund "},
            )
            assert add_res.status_code == 200
            assert add_res.json()["name"] == "refund"

            duplicate_res = await client.post(
                f"/customer-service/conversations/{conversation['id']}/tags/",
                json={"name": "refund"},
            )
            assert duplicate_res.status_code == 200
            assert duplicate_res.json()["id"] == add_res.json()["id"]

            list_res = await client.get(
                f"/customer-service/conversations/{conversation['id']}/tags/"
            )
            assert list_res.status_code == 200
            assert [tag["name"] for tag in list_res.json()] == ["refund"]

            delete_res = await client.delete(
                f"/customer-service/conversations/{conversation['id']}/tags/refund"
            )
            assert delete_res.status_code == 200

            list_after_delete = await client.get(
                f"/customer-service/conversations/{conversation['id']}/tags/"
            )
            assert list_after_delete.json() == []

    finally:
        app.dependency_overrides.pop(get_current_user, None)
