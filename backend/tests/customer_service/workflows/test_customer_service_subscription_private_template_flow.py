from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


async def _seed_clone_and_get_refund_subscription(client):
    await client.post("/customer-service/event-subscriptions/seed-shopify")

    templates = await client.get("/customer-service/workflow-templates")
    assert templates.status_code == 200

    system_refund = next(
        item
        for item in templates.json()
        if item["name"] == "Shopify Refund Request Workflow"
    )

    cloned = await client.post(
        f"/customer-service/workflow-templates/{system_refund['id']}/clone",
        json={"name": f"Private Refund Workflow {uuid4()}"},
    )
    assert cloned.status_code == 200

    subscriptions = await client.get("/customer-service/event-subscriptions")
    assert subscriptions.status_code == 200

    refund_subscription = next(
        item
        for item in subscriptions.json()
        if item["name"] == "Run Shopify refund workflow"
    )

    return cloned.json(), refund_subscription


async def _send_refund_inbound(client):
    inbound = await client.post(
        "/customer-service/omnichannel/inbound",
        json={
            "channel": "chat",
            "external_account_id": f"chat-{uuid4()}",
            "external_thread_id": f"thread-{uuid4()}",
            "external_message_id": f"msg-{uuid4()}",
            "external_customer_id": f"customer-{uuid4()}",
            "customer_name": "Private Workflow Customer",
            "customer_email": f"{uuid4()}@example.com",
            "body": "I want a refund for order #1001",
        },
    )

    assert inbound.status_code == 200
    return inbound.json()


@pytest.mark.asyncio
async def test_subscription_can_point_to_cloned_private_template():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            cloned, subscription = await _seed_clone_and_get_refund_subscription(client)

            published = await client.post(
                f"/customer-service/workflow-templates/{cloned['id']}/publish"
            )

            assert published.status_code == 200
            assert published.json()["status"] == "published"

            updated = await client.patch(
                f"/customer-service/event-subscriptions/{subscription['id']}",
                json={
                    "workflow_template_id": cloned["id"],
                    "workflow_json": None,
                },
            )

            assert updated.status_code == 200
            assert updated.json()["workflow_template_id"] == cloned["id"]

            await _send_refund_inbound(client)

            executions = await client.get("/customer-service/workflow-executions")
            assert executions.status_code == 200

            matched = [
                row
                for row in executions.json()
                if row["subscription_name"] == "Run Shopify refund workflow"
            ]

            assert matched
            assert matched[0]["template_name"] == cloned["name"]
            assert matched[0]["workflow_name"] == cloned["name"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_disabled_subscription_does_not_enqueue_then_enable_enqueues_again():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            _, subscription = await _seed_clone_and_get_refund_subscription(client)

            disabled = await client.post(
                f"/customer-service/event-subscriptions/{subscription['id']}/disable"
            )
            assert disabled.status_code == 200
            assert disabled.json()["is_active"] is False

            await _send_refund_inbound(client)

            executions_after_disabled = await client.get(
                "/customer-service/workflow-executions"
            )
            assert executions_after_disabled.status_code == 200
            assert executions_after_disabled.json() == []

            enabled = await client.post(
                f"/customer-service/event-subscriptions/{subscription['id']}/enable"
            )
            assert enabled.status_code == 200
            assert enabled.json()["is_active"] is True

            await _send_refund_inbound(client)

            executions_after_enabled = await client.get(
                "/customer-service/workflow-executions"
            )
            assert executions_after_enabled.status_code == 200
            assert executions_after_enabled.json()

    finally:
        app.dependency_overrides.pop(get_current_user, None)
