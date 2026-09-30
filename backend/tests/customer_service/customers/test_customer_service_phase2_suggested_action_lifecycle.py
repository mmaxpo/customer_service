from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_suggested_action_accept_execute_lifecycle():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Lifecycle User",
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
                json={
                    "sender_type": "customer",
                    "body": "refund damaged urgent",
                },
            )

            actions_response = await client.post(
                f"/customer-service/conversations/{conversation['id']}/suggested-actions/generate"
            )

            assert actions_response.status_code == 200

            action = next(
                a for a in actions_response.json() if a["action_type"] == "assign"
            )
            assert action["status"] == "suggested"

            accepted = await client.post(
                f"/customer-service/suggested-actions/{action['id']}/accept"
            )

            assert accepted.status_code == 200
            assert accepted.json()["status"] == "accepted"

            executed = await client.post(
                f"/customer-service/suggested-actions/{action['id']}/execute",
                json={"payload": {"assigned_to": str(uuid4())}},
            )

            assert executed.status_code == 200
            assert executed.json()["status"] == "executed"
            assert (
                executed.json()["payload"]["execution_result"]["assigned_to"]
                is not None
            )

            rejected = await client.post(
                f"/customer-service/suggested-actions/{action['id']}/reject"
            )

            assert rejected.status_code == 409

    finally:
        app.dependency_overrides.pop(get_current_user, None)
