from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


async def _create_conversation(client):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Execution User",
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
                "subject": "execution",
            },
        )
    ).json()

    return conversation


async def _create_action(client, conversation_id):
    actions = (
        await client.post(
            f"/customer-service/conversations/{conversation_id}/suggested-actions/generate"
        )
    ).json()

    return actions


@pytest.mark.asyncio
async def test_execute_assign_suggested_action_updates_ticket():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            conversation = await _create_conversation(client)

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "This is urgent and I need help now",
                },
            )

            actions = await _create_action(client, conversation["id"])
            assign_action = next(a for a in actions if a["action_type"] == "assign")

            await client.post(
                f"/customer-service/suggested-actions/{assign_action['id']}/accept"
            )

            execute = await client.post(
                f"/customer-service/suggested-actions/{assign_action['id']}/execute",
                json={"payload": {"assigned_to": str(uuid4())}},
            )

            assert execute.status_code == 200
            body = execute.json()
            assert body["status"] == "executed"
            assert body["payload"]["execution_result"]["assigned_to"] is not None

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_execute_refund_requires_integration():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            conversation = await _create_conversation(client)

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "refund damaged urgent",
                },
            )

            actions = await _create_action(client, conversation["id"])
            refund_action = next(a for a in actions if a["action_type"] == "refund")

            await client.post(
                f"/customer-service/suggested-actions/{refund_action['id']}/accept"
            )

            execute = await client.post(
                f"/customer-service/suggested-actions/{refund_action['id']}/execute",
                json={"payload": {}},
            )

            assert execute.status_code == 501

    finally:
        app.dependency_overrides.pop(get_current_user, None)
