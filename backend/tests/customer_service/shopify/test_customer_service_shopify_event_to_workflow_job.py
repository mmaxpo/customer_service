from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user as get_auth_user
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.role = "owner"


@pytest.mark.asyncio
async def test_shopify_refund_event_subscription_enqueues_workflow_job():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_auth_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            seeded = await client.post(
                "/customer-service/event-subscriptions/seed-shopify"
            )
            assert seeded.status_code == 200

            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "chat",
                    "external_account_id": "chat-shopify-workflow-1",
                    "external_thread_id": f"thread-{uuid4()}",
                    "external_message_id": f"message-{uuid4()}",
                    "external_customer_id": f"customer-{uuid4()}",
                    "customer_name": "Workflow Job Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "I want a refund for order #1001",
                },
            )
            assert inbound.status_code == 200

            jobs = await client.get("/jobs")
            assert jobs.status_code == 200

            workflow_jobs = [
                job for job in jobs.json() if job["job_type"] == "workflow.run"
            ]
            assert workflow_jobs

            matched = [
                job["payload"]
                for job in workflow_jobs
                if job["payload"].get("extras", {}).get("subscription", {}).get("name")
                == "Run Shopify refund workflow"
            ]

            assert matched
            payload = matched[0]

            assert payload["message"] == "I want a refund for order #1001"
            assert payload["extras"]["customer_service"] is True
            assert payload["extras"]["event"]["event_type"] == (
                "customer_service.omnichannel.message.received"
            )
            assert payload["workflow"]["name"] == "Shopify Refund Request Workflow"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_auth_user, None)
