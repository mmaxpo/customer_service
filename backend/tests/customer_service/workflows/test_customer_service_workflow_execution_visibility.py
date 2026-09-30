from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


async def _trigger_refund_workflow_job(client):
    seeded = await client.post("/customer-service/event-subscriptions/seed-shopify")
    assert seeded.status_code == 200

    inbound = await client.post(
        "/customer-service/omnichannel/inbound",
        json={
            "channel": "chat",
            "external_account_id": f"chat-{uuid4()}",
            "external_thread_id": f"thread-{uuid4()}",
            "external_message_id": f"msg-{uuid4()}",
            "external_customer_id": f"customer-{uuid4()}",
            "customer_name": "Workflow Customer",
            "customer_email": f"{uuid4()}@example.com",
            "body": "I want a refund for order #1001",
        },
    )

    assert inbound.status_code == 200

    conversation_id = inbound.json()["conversation_id"]
    ticket_id = inbound.json()["ticket_id"]

    executions = await client.get(
        f"/customer-service/conversations/{conversation_id}/workflow-executions"
    )

    assert executions.status_code == 200
    assert executions.json()

    return {
        "inbound": inbound.json(),
        "conversation_id": conversation_id,
        "ticket_id": ticket_id,
        "execution": executions.json()[0],
    }


@pytest.mark.asyncio
async def test_workflow_execution_list_detail_filters_and_payload_shape():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await _trigger_refund_workflow_job(client)
            execution = created["execution"]

            all_executions = await client.get("/customer-service/workflow-executions")
            assert all_executions.status_code == 200
            assert any(
                row["job_id"] == execution["job_id"] for row in all_executions.json()
            )

            by_conversation = await client.get(
                f"/customer-service/conversations/{created['conversation_id']}/workflow-executions"
            )
            assert by_conversation.status_code == 200
            assert all(
                row["conversation_id"] == created["conversation_id"]
                for row in by_conversation.json()
            )

            by_ticket = await client.get(
                f"/customer-service/tickets/{created['ticket_id']}/workflow-executions"
            )
            assert by_ticket.status_code == 200
            assert all(
                row["ticket_id"] == created["ticket_id"] for row in by_ticket.json()
            )

            detail = await client.get(
                f"/customer-service/workflow-executions/{execution['job_id']}"
            )
            assert detail.status_code == 200

            data = detail.json()

            assert data["job_type"] == "workflow.run"
            assert data["status"] == "queued"
            assert data["template_name"] == "Shopify Refund Request Workflow"
            assert data["workflow_name"] == "Shopify Refund Request Workflow"
            assert data["subscription_name"] == "Run Shopify refund workflow"
            assert data["trigger_event_type"] == (
                "customer_service.omnichannel.message.received"
            )
            assert data["conversation_id"] == created["conversation_id"]
            assert data["ticket_id"] == created["ticket_id"]
            assert data["channel"] == "chat"
            assert data["message"] == "I want a refund for order #1001"

            payload = data["payload"]

            assert payload["message"] == "I want a refund for order #1001"
            assert payload["thread_id"] == created["conversation_id"]
            assert payload["workflow"]["name"] == "Shopify Refund Request Workflow"
            assert payload["extras"]["customer_service"] is True
            assert payload["extras"]["subscription"]["name"] == (
                "Run Shopify refund workflow"
            )

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_workflow_execution_empty_and_not_found_are_safe():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            empty = await client.get(
                f"/customer-service/conversations/{uuid4()}/workflow-executions"
            )
            assert empty.status_code == 200
            assert empty.json() == []

            missing = await client.get(
                f"/customer-service/workflow-executions/{uuid4()}"
            )
            assert missing.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_workflow_execution_is_user_scoped():
    user_a = FakeUser()
    user_b = FakeUser()

    app.dependency_overrides[get_current_user] = lambda: user_a

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await _trigger_refund_workflow_job(client)
            job_id = created["execution"]["job_id"]

            app.dependency_overrides[get_current_user] = lambda: user_b

            hidden = await client.get(f"/customer-service/workflow-executions/{job_id}")

            assert hidden.status_code == 404

            listed = await client.get("/customer-service/workflow-executions")

            assert listed.status_code == 200
            assert all(row["job_id"] != job_id for row in listed.json())

    finally:
        app.dependency_overrides.pop(get_current_user, None)
