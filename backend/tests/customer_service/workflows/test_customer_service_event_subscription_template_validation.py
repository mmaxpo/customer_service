from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_event_subscription_rejects_missing_or_unpublished_template_reference():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            missing = await client.post(
                "/customer-service/event-subscriptions",
                json={
                    "name": "Missing template subscription",
                    "event_type": "customer_service.omnichannel.message.received",
                    "workflow_template_id": str(uuid4()),
                    "filters": {"keywords": ["refund"]},
                },
            )

            assert missing.status_code == 422

            await client.post("/customer-service/workflow-templates/seed-shopify")

            templates = await client.get("/customer-service/workflow-templates")
            source = next(
                item
                for item in templates.json()
                if item["name"] == "Shopify Refund Request Workflow"
            )

            cloned = await client.post(
                f"/customer-service/workflow-templates/{source['id']}/clone",
                json={"name": f"Draft Only Template {uuid4()}"},
            )
            assert cloned.status_code == 200
            assert cloned.json()["status"] == "draft"

            draft_ref = await client.post(
                "/customer-service/event-subscriptions",
                json={
                    "name": "Draft template subscription",
                    "event_type": "customer_service.omnichannel.message.received",
                    "workflow_template_id": cloned.json()["id"],
                    "filters": {"keywords": ["refund"]},
                },
            )

            assert draft_ref.status_code == 422

    finally:
        app.dependency_overrides.pop(get_current_user, None)
