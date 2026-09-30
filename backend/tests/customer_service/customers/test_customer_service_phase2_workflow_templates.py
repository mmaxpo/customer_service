from uuid import uuid4
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_workflow_template_create():

    user = FakeUser()

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/customer-service/workflow-templates",
                json={
                    "category": "refund",
                    "name": "Refund Workflow",
                    "workflow_json": {
                        "nodes": [
                            {
                                "id": "trigger",
                                "data": {
                                    "nodeType": "trigger.message",
                                    "message": "hello",
                                },
                            },
                            {
                                "id": "response",
                                "data": {
                                    "nodeType": "response",
                                    "value": "ok",
                                },
                            },
                        ],
                        "edges": [
                            {
                                "id": "e1",
                                "source": "trigger",
                                "target": "response",
                            }
                        ],
                    },
                },
            )

            assert r.status_code == 200, r.text

            data = r.json()

            assert data["name"] == "Refund Workflow"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
