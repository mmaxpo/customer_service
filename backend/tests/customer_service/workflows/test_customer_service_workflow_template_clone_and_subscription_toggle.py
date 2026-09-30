from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_clone_shopify_system_template_creates_private_draft():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            seeded = await client.post(
                "/customer-service/workflow-templates/seed-shopify"
            )
            assert seeded.status_code == 200

            listed = await client.get("/customer-service/workflow-templates")
            assert listed.status_code == 200

            source = next(
                item
                for item in listed.json()
                if item["name"] == "Shopify Refund Request Workflow"
            )

            cloned = await client.post(
                f"/customer-service/workflow-templates/{source['id']}/clone",
                json={
                    "name": "My Custom Refund Workflow",
                    "description": "Private merchant refund workflow",
                },
            )

            assert cloned.status_code == 200

            data = cloned.json()

            assert data["name"] == "My Custom Refund Workflow"
            assert data["description"] == "Private merchant refund workflow"
            assert data["category"] == source["category"]
            assert data["workflow_json"]["name"] == "My Custom Refund Workflow"

            source_without_name = dict(source["workflow_json"])
            data_without_name = dict(data["workflow_json"])
            source_without_name.pop("name", None)
            data_without_name.pop("name", None)

            assert data_without_name == source_without_name
            assert data["scope"] == "private"
            assert data["status"] == "draft"

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_event_subscription_disable_and_enable():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            seeded = await client.post(
                "/customer-service/event-subscriptions/seed-shopify"
            )
            assert seeded.status_code == 200

            subscription = seeded.json()["created"][0]
            subscription_id = subscription["id"]

            disabled = await client.post(
                f"/customer-service/event-subscriptions/{subscription_id}/disable"
            )

            assert disabled.status_code == 200
            assert disabled.json()["is_active"] is False

            enabled = await client.post(
                f"/customer-service/event-subscriptions/{subscription_id}/enable"
            )

            assert enabled.status_code == 200
            assert enabled.json()["is_active"] is True

    finally:
        app.dependency_overrides.pop(get_current_user, None)
