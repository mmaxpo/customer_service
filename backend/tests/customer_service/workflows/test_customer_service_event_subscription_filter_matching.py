from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


async def _create_subscription(client, *, name, filters):
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
            "filters": filters,
            "is_active": True,
        },
    )
    assert response.status_code == 200
    return response.json()


async def _send_inbound(client, *, body, customer_email=None, workflow=None):
    response = await client.post(
        "/customer-service/omnichannel/inbound",
        json={
            "channel": "chat",
            "external_account_id": f"chat-{uuid4()}",
            "external_thread_id": f"thread-{uuid4()}",
            "external_message_id": f"msg-{uuid4()}",
            "external_customer_id": f"customer-{uuid4()}",
            "customer_name": "Filter Customer",
            "customer_email": customer_email or f"{uuid4()}@example.com",
            "body": body,
            "meta": {"workflow": workflow} if workflow is not None else {},
        },
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_event_subscription_keyword_filter_matches_and_misses():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await _create_subscription(
                client,
                name="Refund keyword workflow",
                filters={"keywords": ["refund"]},
            )

            matched_inbound = await _send_inbound(
                client,
                body="I need a refund for my order",
            )

            matched_executions = await client.get(
                f"/customer-service/conversations/{matched_inbound['conversation_id']}/workflow-executions"
            )
            assert matched_executions.status_code == 200
            assert len(matched_executions.json()) == 1

            missed_inbound = await _send_inbound(
                client,
                body="Where is my package?",
            )

            missed_executions = await client.get(
                f"/customer-service/conversations/{missed_inbound['conversation_id']}/workflow-executions"
            )
            assert missed_executions.status_code == 200
            assert missed_executions.json() == []

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_event_subscription_customer_email_and_ticket_priority_filters():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await _create_subscription(
                client,
                name="VIP urgent workflow",
                filters={
                    "customer_email": "customer@example.com",
                    "ticket_priority": "urgent",
                },
            )

            matched_inbound = await _send_inbound(
                client,
                body="I need help urgently",
                customer_email="customer@example.com",
                workflow={"action": {"ticket_priority": "urgent"}},
            )

            matched_executions = await client.get(
                f"/customer-service/conversations/{matched_inbound['conversation_id']}/workflow-executions"
            )
            assert matched_executions.status_code == 200
            assert len(matched_executions.json()) == 1

            missed_inbound = await _send_inbound(
                client,
                body="I need help urgently",
                customer_email="customer@example.com",
                workflow={"action": {"ticket_priority": "normal"}},
            )

            missed_executions = await client.get(
                f"/customer-service/conversations/{missed_inbound['conversation_id']}/workflow-executions"
            )
            assert missed_executions.status_code == 200
            assert missed_executions.json() == []

    finally:
        app.dependency_overrides.pop(get_current_user, None)
