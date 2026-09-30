from uuid import uuid4
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):

        self.id = uuid4()


@pytest.mark.asyncio
async def test_generate_actions():

    user = FakeUser()

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "test",
                        "email": f"{uuid4()}@test.com",
                        "phone": "111",
                    },
                )
            ).json()

            conversation = (
                await client.post(
                    "/customer-service/conversations/",
                    json={
                        "customer_id": customer["id"],
                        "channel": "chat",
                        "subject": "refund",
                    },
                )
            ).json()

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={"sender_type": "customer", "body": "refund damaged urgent"},
            )

            r = await client.post(
                f"/customer-service/conversations/{conversation['id']}/suggested-actions/generate"
            )

            assert r.status_code == 200

            actions = r.json()

            assert len(actions) > 0

    finally:
        app.dependency_overrides.pop(get_current_user, None)
