from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


async def _create_subscription(client, *, name, keyword):
    response = await client.post(
        "/customer-service/event-subscriptions",
        json={
            "name": name,
            "event_type": "customer_service.omnichannel.message.received",
            "workflow_json": {
                "name": name,
                "nodes": [
                    {
                        "id": "trigger",
                        "data": {"nodeType": "trigger.message"},
                    }
                ],
                "edges": [],
            },
            "filters": {"keywords": [keyword]},
            "is_active": True,
        },
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_matching_event_fans_out_to_multiple_workflow_jobs():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await _create_subscription(
                client,
                name="Refund workflow A",
                keyword="refund",
            )
            await _create_subscription(
                client,
                name="Refund workflow B",
                keyword="refund",
            )
            await _create_subscription(
                client,
                name="Refund workflow C",
                keyword="refund",
            )

            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "chat",
                    "external_account_id": f"chat-{uuid4()}",
                    "external_thread_id": f"thread-{uuid4()}",
                    "external_message_id": f"msg-{uuid4()}",
                    "external_customer_id": f"customer-{uuid4()}",
                    "customer_name": "Fanout Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "I want a refund for order #1001",
                },
            )

            assert inbound.status_code == 200

            executions = await client.get(
                f"/customer-service/conversations/{inbound.json()['conversation_id']}/workflow-executions"
            )

            assert executions.status_code == 200

            names = {row["subscription_name"] for row in executions.json()}

            assert {
                "Refund workflow A",
                "Refund workflow B",
                "Refund workflow C",
            }.issubset(names)

            assert len(executions.json()) == 3

    finally:
        app.dependency_overrides.pop(get_current_user, None)
