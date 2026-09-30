from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_subscription_does_not_run_private_draft_template():
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

            cloned = await client.post(
                f"/customer-service/workflow-templates/{source['id']}/clone",
                json={"name": f"Draft Private Refund Workflow {uuid4()}"},
            )
            assert cloned.status_code == 200
            assert cloned.json()["status"] == "draft"

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
            assert repointed.status_code == 422
            assert "published accessible template" in repointed.json()["detail"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)
