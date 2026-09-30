from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_subscription_runs_published_private_template():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post("/customer-service/event-subscriptions/seed-shopify")

            templates = await client.get("/customer-service/workflow-templates")
            source = next(
                item
                for item in templates.json()
                if item["name"] == "Shopify Refund Request Workflow"
            )

            clone_name = f"Published Private Refund Workflow {uuid4()}"
            cloned = await client.post(
                f"/customer-service/workflow-templates/{source['id']}/clone",
                json={"name": clone_name},
            )
            assert cloned.status_code == 200

            publish = await client.post(
                f"/customer-service/workflow-templates/{cloned.json()['id']}/publish"
            )
            assert publish.status_code == 200
            assert publish.json()["status"] == "published"

            subscriptions = await client.get("/customer-service/event-subscriptions")
            refund_subscription = next(
                item
                for item in subscriptions.json()
                if item["name"] == "Run Shopify refund workflow"
            )

            repointed = await client.patch(
                f"/customer-service/event-subscriptions/{refund_subscription['id']}",
                json={
                    "workflow_template_id": cloned.json()["id"],
                    "workflow_json": None,
                },
            )
            assert repointed.status_code == 200

            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "chat",
                    "external_account_id": f"chat-{uuid4()}",
                    "external_thread_id": f"thread-{uuid4()}",
                    "external_message_id": f"msg-{uuid4()}",
                    "external_customer_id": f"customer-{uuid4()}",
                    "customer_name": "Published Private Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "I want a refund for order #1001",
                },
            )
            assert inbound.status_code == 200

            executions = await client.get(
                f"/customer-service/conversations/{inbound.json()['conversation_id']}/workflow-executions"
            )
            assert executions.status_code == 200
            assert executions.json()

            execution = executions.json()[0]
            assert execution["template_name"] == clone_name
            assert execution["workflow_name"] == clone_name
            assert execution["payload"]["workflow"]["name"] == clone_name

    finally:
        app.dependency_overrides.pop(get_current_user, None)
