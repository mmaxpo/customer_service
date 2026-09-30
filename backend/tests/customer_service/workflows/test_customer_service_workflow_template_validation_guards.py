import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        from uuid import uuid4

        self.id = uuid4()
        self.email = "workflow-template-validation@example.com"


INVALID_WORKFLOW = {
    "nodes": [
        {"id": "trigger", "type": "trigger.message", "data": {}},
        {"id": "a", "type": "set.variable", "data": {"key": "x", "value": "A"}},
        {"id": "b", "type": "set.variable", "data": {"key": "y", "value": "B"}},
    ],
    "edges": [
        {"id": "e1", "source": "trigger", "target": "a"},
        {"id": "e2", "source": "a", "target": "b"},
        {"id": "e3", "source": "b", "target": "a"},
    ],
}


@pytest.mark.asyncio
async def test_create_rejects_invalid_workflow():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/customer-service/workflow-templates",
                json={
                    "category": "shopify",
                    "name": "Bad Workflow",
                    "workflow_json": INVALID_WORKFLOW,
                    "tags": [],
                },
            )

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "invalid_workflow_template"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_update_rejects_invalid_workflow():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post("/customer-service/workflow-templates/seed-shopify")

            listed = await client.get("/customer-service/workflow-templates")
            assert listed.status_code == 200

            source = next(item for item in listed.json() if item["scope"] == "system")

            cloned = await client.post(
                f"/customer-service/workflow-templates/{source['id']}/clone",
                json={"name": "Draft Bad Workflow Guard"},
            )
            assert cloned.status_code == 200

            response = await client.patch(
                f"/customer-service/workflow-templates/{cloned.json()['id']}",
                json={"workflow_json": INVALID_WORKFLOW},
            )

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "invalid_workflow_template"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
