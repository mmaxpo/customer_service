from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.api.auth import get_current_user
from app.models.models import PlatformJob


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_manual_conversation_workflow_template_run_enqueues_workflow_job():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "shopify",
                    "external_account_id": f"shop-{uuid4()}",
                    "external_thread_id": f"thread-{uuid4()}",
                    "external_message_id": f"msg-{uuid4()}",
                    "external_customer_id": f"customer-{uuid4()}",
                    "customer_name": "Manual Workflow Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "My order arrived damaged. Please help me with a refund.",
                },
            )
            assert created.status_code == 200, created.text
            conversation_id = created.json()["conversation_id"]
            customer_id = created.json()["customer_id"]

            template = await client.post(
                "/customer-service/workflow-templates",
                json={
                    "category": "support",
                    "name": "Manual Refund Workflow",
                    "description": "Manual workflow test",
                    "workflow_json": {
                        "name": "Manual Refund Workflow",
                        "nodes": [
                            {
                                "id": "trigger",
                                "type": "custom",
                                "position": {"x": 0, "y": 0},
                                "data": {
                                    "nodeType": "trigger.message",
                                    "input": "test",
                                },
                            },
                            {
                                "id": "response",
                                "type": "custom",
                                "position": {"x": 250, "y": 0},
                                "data": {
                                    "nodeType": "response",
                                    "answer": "Manual workflow queued.",
                                },
                            },
                        ],
                        "edges": [
                            {
                                "id": "trigger-response",
                                "source": "trigger",
                                "target": "response",
                            }
                        ],
                    },
                    "input_schema": {},
                    "output_schema": {},
                    "tags": ["manual"],
                },
            )
            assert template.status_code == 200, template.text
            template_id = template.json()["id"]

            published = await client.post(
                f"/customer-service/workflow-templates/{template_id}/publish"
            )
            assert published.status_code == 200, published.text

            response = await client.post(
                f"/customer-service/conversations/{conversation_id}/workflow-executions/run-template",
                json={
                    "template_id": template_id,
                },
            )

            assert response.status_code == 200, response.text
            body = response.json()

            assert body["job_type"] == "workflow.run"
            assert body["status"] == "queued"
            assert body["conversation_id"] == conversation_id
            assert body["customer_id"] == customer_id
            assert body["channel"] == "shopify"
            assert body["workflow_name"] == "Manual Refund Workflow"
            assert body["template_name"] == "Manual Refund Workflow"
            assert (
                body["message"]
                == "My order arrived damaged. Please help me with a refund."
            )

            detail = await client.get(
                f"/customer-service/workflow-executions/{body['job_id']}"
            )
            assert detail.status_code == 200
            payload = detail.json()["payload"]

            assert payload["thread_id"] == conversation_id
            assert payload["extras"]["manual_trigger"] is True
            assert (
                payload["extras"]["event"]["event_type"]
                == "conversation.workflow_template.manual_run"
            )
            assert (
                payload["extras"]["event"]["payload"]["conversation_id"]
                == conversation_id
            )
            assert payload["extras"]["template"]["id"] == template_id

    finally:
        app.dependency_overrides.clear()
