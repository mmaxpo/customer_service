from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_private_template_lifecycle_is_user_scoped():
    user_a = FakeUser()
    user_b = FakeUser()

    app.dependency_overrides[get_current_user] = lambda: user_a

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post("/customer-service/workflow-templates/seed-shopify")

            templates = await client.get("/customer-service/workflow-templates")
            assert templates.status_code == 200

            source = next(
                item
                for item in templates.json()
                if item["name"] == "Shopify Refund Request Workflow"
            )

            cloned = await client.post(
                f"/customer-service/workflow-templates/{source['id']}/clone",
                json={"name": f"User A Private Workflow {uuid4()}"},
            )
            assert cloned.status_code == 200

            template_id = cloned.json()["id"]

            app.dependency_overrides[get_current_user] = lambda: user_b

            update = await client.patch(
                f"/customer-service/workflow-templates/{template_id}",
                json={"name": "User B Attack Edit"},
            )
            assert update.status_code == 404

            publish = await client.post(
                f"/customer-service/workflow-templates/{template_id}/publish"
            )
            assert publish.status_code == 404

            unpublish = await client.post(
                f"/customer-service/workflow-templates/{template_id}/unpublish"
            )
            assert unpublish.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)
