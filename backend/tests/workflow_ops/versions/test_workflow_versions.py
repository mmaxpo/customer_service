from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import get_db
from app.main import app
from app.api.auth import get_current_user
from app.workflow_operations.versions.schemas import (
    WorkflowDefinitionCreate,
    WorkflowVersionCreate,
)
from app.workflow_operations.versions.service import WorkflowVersionService


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "workflow-version@test.com"


def _workflow(answer: str):
    return {
        "nodes": [
            {"id": "trigger", "data": {"nodeType": "trigger.message"}},
            {
                "id": "set_result",
                "data": {"nodeType": "set.variable", "key": "result", "value": answer},
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "result",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger", "target": "set_result"},
            {"id": "e2", "source": "set_result", "target": "response"},
        ],
    }


@pytest.mark.asyncio
async def test_workflow_version_publish_and_rollback_service():
    user_id = uuid4()

    async for db in get_db():
        service = WorkflowVersionService(db)

        definition = await service.create_definition(
            user_id=user_id,
            payload=WorkflowDefinitionCreate(
                name="Refund workflow",
                slug=f"refund-{uuid4()}",
                description="Refund automation",
            ),
        )

        v1 = await service.create_version(
            definition_id=definition["id"],
            user_id=user_id,
            payload=WorkflowVersionCreate(
                workflow_json=_workflow("V1"),
                notes="first version",
            ),
        )

        v2 = await service.create_version(
            definition_id=definition["id"],
            user_id=user_id,
            payload=WorkflowVersionCreate(
                workflow_json=_workflow("V2"),
                notes="second version",
                evaluation_summary={"score": 1.0},
            ),
        )

        assert v1["version"] == 1
        assert v2["version"] == 2
        assert v1["status"] == "draft"
        assert v2["status"] == "draft"

        published_v2 = await service.publish_version(
            definition_id=definition["id"],
            user_id=user_id,
            version=2,
        )

        assert published_v2["status"] == "published"

        active = await service.get_active_version(
            definition_id=definition["id"],
            user_id=user_id,
        )

        assert active is not None
        assert active["version"] == 2
        assert active["workflow_json"]["nodes"][1]["data"]["value"] == "V2"

        rollback_v1 = await service.rollback(
            definition_id=definition["id"],
            user_id=user_id,
            version=1,
        )

        assert rollback_v1["status"] == "published"

        active_after_rollback = await service.get_active_version(
            definition_id=definition["id"],
            user_id=user_id,
        )

        assert active_after_rollback is not None
        assert active_after_rollback["version"] == 1
        assert (
            active_after_rollback["workflow_json"]["nodes"][1]["data"]["value"] == "V1"
        )

        old_v2 = await service.repo.get_version(
            definition_id=definition["id"],
            version=2,
        )

        assert old_v2 is not None
        assert old_v2["status"] == "archived"

        break


@pytest.mark.asyncio
async def test_workflow_versions_endpoint_create_publish_active():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            definition_response = await client.post(
                "/workflow-versions/definitions",
                json={
                    "name": "Shipping workflow",
                    "slug": f"shipping-{uuid4()}",
                    "description": "Shipping automation",
                },
            )

            assert definition_response.status_code == 200, definition_response.text

            definition = definition_response.json()

            version_response = await client.post(
                f"/workflow-versions/definitions/{definition['id']}/versions",
                json={
                    "workflow_json": _workflow("API_V1"),
                    "notes": "api version",
                },
            )

            assert version_response.status_code == 200, version_response.text

            version = version_response.json()

            assert version["version"] == 1
            assert version["status"] == "draft"

            publish_response = await client.post(
                f"/workflow-versions/definitions/{definition['id']}/versions/1/publish"
            )

            assert publish_response.status_code == 200, publish_response.text
            assert publish_response.json()["status"] == "published"

            active_response = await client.get(
                f"/workflow-versions/definitions/{definition['id']}/active"
            )

            assert active_response.status_code == 200, active_response.text
            assert active_response.json()["version"] == 1

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_workflow_versions_list_rejects_foreign_definition():
    owner = FakeUser()
    foreign = FakeUser()

    app.dependency_overrides[get_current_user] = lambda: owner

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            definition_response = await client.post(
                "/workflow-versions/definitions",
                json={
                    "name": "Private workflow",
                    "slug": f"private-{uuid4()}",
                    "description": "Owner-only workflow",
                },
            )

            assert definition_response.status_code == 200
            definition = definition_response.json()

            version_response = await client.post(
                f"/workflow-versions/definitions/{definition['id']}/versions",
                json={
                    "workflow_json": _workflow("OWNER_PRIVATE"),
                    "notes": "private notes",
                    "evaluation_summary": {
                        "score": 1.0,
                        "private": True,
                    },
                    "metadata_json": {
                        "owner_only": True,
                    },
                },
            )

            assert version_response.status_code == 200

            owner_versions = await client.get(
                f"/workflow-versions/definitions/{definition['id']}/versions"
            )

            assert owner_versions.status_code == 200
            assert len(owner_versions.json()) == 1
            assert (
                owner_versions.json()[0]["workflow_json"]["nodes"][1]["data"]["value"]
                == "OWNER_PRIVATE"
            )

            app.dependency_overrides[get_current_user] = lambda: foreign

            foreign_versions = await client.get(
                f"/workflow-versions/definitions/{definition['id']}/versions"
            )

            assert foreign_versions.status_code == 403
            assert foreign_versions.json()["detail"] == "workflow_definition_forbidden"

            missing_versions = await client.get(
                f"/workflow-versions/definitions/{uuid4()}/versions"
            )

            assert missing_versions.status_code == 404
            assert missing_versions.json()["detail"] == "workflow_definition_not_found"

    finally:
        app.dependency_overrides.clear()
