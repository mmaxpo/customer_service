import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


async def _create_subscription(client, *, name, keywords=None, workflow_json=None):
    response = await client.post(
        "/customer-service/event-subscriptions",
        json={
            "name": name,
            "event_type": "customer_service.omnichannel.message.received",
            "workflow_json": workflow_json
            or {
                "name": name,
                "nodes": [{"id": "trigger", "data": {"nodeType": "trigger.message"}}],
                "edges": [],
            },
            "filters": {"keywords": keywords or ["refund"]},
            "is_active": True,
        },
    )
    assert response.status_code == 200
    return response.json()


async def _send_refund(client, *, suffix=None):
    unique = suffix or str(uuid4())
    response = await client.post(
        "/customer-service/omnichannel/inbound",
        json={
            "channel": "chat",
            "external_account_id": f"chat-{unique}",
            "external_thread_id": f"thread-{unique}",
            "external_message_id": f"msg-{unique}",
            "external_customer_id": f"customer-{unique}",
            "customer_name": "Confidence Customer",
            "customer_email": f"{unique}@example.com",
            "body": "I want a refund for order #1001",
        },
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_concurrent_inbound_refund_events_create_expected_executions():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post("/customer-service/event-subscriptions/seed-shopify")

            results = await asyncio.gather(
                *[
                    _send_refund(client, suffix=f"concurrent-{uuid4()}")
                    for _ in range(10)
                ]
            )

            executions = await client.get("/customer-service/workflow-executions")
            assert executions.status_code == 200

            refund_executions = [
                row
                for row in executions.json()
                if row["subscription_name"] == "Run Shopify refund workflow"
            ]

            conversation_ids = {str(item["conversation_id"]) for item in results}
            execution_conversation_ids = {
                row["conversation_id"] for row in refund_executions
            }

            assert conversation_ids.issubset(execution_conversation_ids)
            assert len(conversation_ids) == 10

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_disabled_subscription_never_runs_then_enable_runs():
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

            subscription = next(
                item
                for item in seed.json()["created"]
                if item["name"] == "Run Shopify refund workflow"
            )

            disabled = await client.post(
                f"/customer-service/event-subscriptions/{subscription['id']}/disable"
            )
            assert disabled.status_code == 200

            disabled_inbound = await _send_refund(client, suffix=f"disabled-{uuid4()}")
            disabled_exec = await client.get(
                f"/customer-service/conversations/{disabled_inbound['conversation_id']}/workflow-executions"
            )
            assert disabled_exec.status_code == 200
            assert disabled_exec.json() == []

            enabled = await client.post(
                f"/customer-service/event-subscriptions/{subscription['id']}/enable"
            )
            assert enabled.status_code == 200

            enabled_inbound = await _send_refund(client, suffix=f"enabled-{uuid4()}")
            enabled_exec = await client.get(
                f"/customer-service/conversations/{enabled_inbound['conversation_id']}/workflow-executions"
            )
            assert enabled_exec.status_code == 200
            assert len(enabled_exec.json()) == 1

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_three_matching_subscriptions_fan_out_to_three_jobs():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await _create_subscription(
                client, name="Refund automation", keywords=["refund"]
            )
            await _create_subscription(
                client, name="VIP refund automation", keywords=["refund"]
            )
            await _create_subscription(
                client, name="Escalation refund automation", keywords=["refund"]
            )

            inbound = await _send_refund(client, suffix=f"fanout3-{uuid4()}")

            executions = await client.get(
                f"/customer-service/conversations/{inbound['conversation_id']}/workflow-executions"
            )
            assert executions.status_code == 200

            names = {row["subscription_name"] for row in executions.json()}
            assert names == {
                "Refund automation",
                "VIP refund automation",
                "Escalation refund automation",
            }
            assert len(executions.json()) == 3

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_workflow_execution_pagination_has_no_overlap():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post("/customer-service/event-subscriptions/seed-shopify")

            for _ in range(25):
                await _send_refund(client, suffix=f"page-{uuid4()}")

            first_page = await client.get(
                "/customer-service/workflow-executions?limit=10&offset=0"
            )
            second_page = await client.get(
                "/customer-service/workflow-executions?limit=10&offset=10"
            )

            assert first_page.status_code == 200
            assert second_page.status_code == 200
            assert len(first_page.json()) == 10
            assert len(second_page.json()) == 10

            first_ids = {row["job_id"] for row in first_page.json()}
            second_ids = {row["job_id"] for row in second_page.json()}

            assert first_ids.isdisjoint(second_ids)

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_workflow_execution_conversation_endpoint_is_user_scoped():
    user_a = FakeUser()
    user_b = FakeUser()

    app.dependency_overrides[get_current_user] = lambda: user_a

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post("/customer-service/event-subscriptions/seed-shopify")
            inbound = await _send_refund(client, suffix=f"scope-{uuid4()}")

            app.dependency_overrides[get_current_user] = lambda: user_b

            hidden = await client.get(
                f"/customer-service/conversations/{inbound['conversation_id']}/workflow-executions"
            )

            assert hidden.status_code == 200
            assert hidden.json() == []

    finally:
        app.dependency_overrides.pop(get_current_user, None)
