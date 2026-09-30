from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_workflow_execution_preserves_event_subscription_and_entity_metadata():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            seed = await client.post(
                "/customer-service/event-subscriptions/seed-shopify"
            )
            assert seed.status_code == 200

            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "chat",
                    "external_account_id": f"chat-{uuid4()}",
                    "external_thread_id": f"thread-{uuid4()}",
                    "external_message_id": f"msg-{uuid4()}",
                    "external_customer_id": f"customer-{uuid4()}",
                    "customer_name": "Metadata Customer",
                    "customer_email": "metadata@example.com",
                    "body": "I want a refund for order #1001",
                },
            )

            assert inbound.status_code == 200
            inbound_data = inbound.json()

            executions = await client.get(
                f"/customer-service/conversations/{inbound_data['conversation_id']}/workflow-executions"
            )
            assert executions.status_code == 200
            assert executions.json()

            execution = executions.json()[0]

            assert execution["conversation_id"] == inbound_data["conversation_id"]
            assert execution["ticket_id"] == inbound_data["ticket_id"]
            assert execution["customer_id"] == inbound_data["customer_id"]
            assert execution["channel"] == "chat"
            assert execution["trigger_event_type"] == (
                "customer_service.omnichannel.message.received"
            )
            assert execution["subscription_name"] == "Run Shopify refund workflow"
            assert execution["template_name"] == "Shopify Refund Request Workflow"

            payload = execution["payload"]
            event = payload["extras"]["event"]

            assert event["source"] == "customer_service.omnichannel"
            assert (
                event["payload"]["conversation_id"] == inbound_data["conversation_id"]
            )
            assert event["payload"]["ticket_id"] == inbound_data["ticket_id"]
            assert event["payload"]["customer_id"] == inbound_data["customer_id"]
            assert event["payload"]["customer_email"] == "metadata@example.com"

            subscription = payload["extras"]["subscription"]
            assert subscription["name"] == "Run Shopify refund workflow"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
