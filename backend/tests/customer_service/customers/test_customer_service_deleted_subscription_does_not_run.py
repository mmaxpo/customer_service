from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_deleted_subscription_does_not_create_workflow_execution():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/customer-service/event-subscriptions",
                json={
                    "name": "Temporary refund automation",
                    "event_type": "customer_service.omnichannel.message.received",
                    "workflow_json": {
                        "name": "Temporary refund automation",
                        "nodes": [
                            {
                                "id": "trigger",
                                "data": {"nodeType": "trigger.message"},
                            }
                        ],
                        "edges": [],
                    },
                    "filters": {"keywords": ["refund"]},
                    "is_active": True,
                },
            )
            assert created.status_code == 200

            deleted = await client.delete(
                f"/customer-service/event-subscriptions/{created.json()['id']}"
            )
            assert deleted.status_code == 204

            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "chat",
                    "external_account_id": f"chat-{uuid4()}",
                    "external_thread_id": f"thread-{uuid4()}",
                    "external_message_id": f"msg-{uuid4()}",
                    "external_customer_id": f"customer-{uuid4()}",
                    "customer_name": "Deleted Subscription Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "I want a refund for order #1001",
                },
            )
            assert inbound.status_code == 200

            executions = await client.get(
                f"/customer-service/conversations/{inbound.json()['conversation_id']}/workflow-executions"
            )
            assert executions.status_code == 200
            assert executions.json() == []

    finally:
        app.dependency_overrides.pop(get_current_user, None)
