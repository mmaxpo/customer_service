from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


async def _clone_refund_template(client):
    await client.post("/customer-service/workflow-templates/seed-shopify")

    listed = await client.get("/customer-service/workflow-templates")
    assert listed.status_code == 200

    source = next(
        item
        for item in listed.json()
        if item["name"] == "Shopify Refund Request Workflow"
    )

    cloned = await client.post(
        f"/customer-service/workflow-templates/{source['id']}/clone",
        json={"name": f"Merchant Refund Workflow {uuid4()}"},
    )
    assert cloned.status_code == 200

    return source, cloned.json()


@pytest.mark.asyncio
async def test_private_template_update_publish_unpublish_lifecycle():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            _, template = await _clone_refund_template(client)

            updated = await client.patch(
                f"/customer-service/workflow-templates/{template['id']}",
                json={
                    "name": "Updated Merchant Refund Workflow",
                    "tags": ["shopify", "refund", "custom"],
                },
            )

            assert updated.status_code == 200
            assert updated.json()["name"] == "Updated Merchant Refund Workflow"
            assert updated.json()["tags"] == ["shopify", "refund", "custom"]
            assert updated.json()["status"] == "draft"

            published = await client.post(
                f"/customer-service/workflow-templates/{template['id']}/publish"
            )

            assert published.status_code == 200
            assert published.json()["status"] == "published"

            blocked_update = await client.patch(
                f"/customer-service/workflow-templates/{template['id']}",
                json={"name": "Should Not Update Published Template"},
            )

            assert blocked_update.status_code == 409

            unpublished = await client.post(
                f"/customer-service/workflow-templates/{template['id']}/unpublish"
            )

            assert unpublished.status_code == 200
            assert unpublished.json()["status"] == "draft"

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_system_template_is_immutable_for_user_lifecycle_actions():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            source, _ = await _clone_refund_template(client)

            update_system = await client.patch(
                f"/customer-service/workflow-templates/{source['id']}",
                json={"name": "Attempted System Edit"},
            )

            assert update_system.status_code == 403

            publish_system = await client.post(
                f"/customer-service/workflow-templates/{source['id']}/publish"
            )

            assert publish_system.status_code == 403

    finally:
        app.dependency_overrides.pop(get_current_user, None)
