from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.core.session import get_db
from app.main import app
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker
from app.runtime.nodes.registry.builtins import register_builtin_nodes


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "timeline@test.com"


def _workflow():
    return {
        "nodes": [
            {
                "id": "trigger",
                "data": {"nodeType": "trigger.message", "input": "start"},
            },
            {
                "id": "set_result",
                "data": {
                    "nodeType": "set.variable",
                    "key": "result",
                    "value": "TIMELINE_OK",
                },
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
async def test_workflow_run_timeline_combines_events_and_snapshots():
    register_builtin_nodes()

    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async for db in get_db():
            job = await JobService(db).enqueue(
                user_id=user.id,
                job_type="workflow.run",
                payload={
                    "workflow": _workflow(),
                    "message": "start",
                    "thread_id": str(uuid4()),
                },
            )

            result_job = await JobWorker(
                db,
                worker_id=f"timeline-worker-{uuid4()}",
            ).run_once(job_id=job.id)

            assert result_job.status == "succeeded", result_job.error_message
            assert result_job.result["meta"]["status"] == "ok"

            workflow_run_id = result_job.result["meta"]["workflow_run_id"]

            break

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(f"/workflows/runs/{workflow_run_id}/timeline")

            assert response.status_code == 200, response.text

            body = response.json()

            assert body["workflow_run_id"] == workflow_run_id
            assert body["status"] in {"done", "completed"}

            item_types = [item["type"] for item in body["items"]]

            assert "run_start" in item_types
            assert "node_start" in item_types
            assert "node_end" in item_types
            assert "run_completed" in item_types

            snapshot_items = [
                item for item in body["items"] if item["source"] == "snapshot"
            ]

            assert snapshot_items
            assert body["counts"]["snapshots"] >= 1
            assert body["counts"]["events"] >= 1
            assert body["counts"]["items"] == len(body["items"])

            foreign_user = FakeUser()
            app.dependency_overrides[get_current_user] = lambda: foreign_user

            foreign_response = await client.get(
                f"/workflows/runs/{workflow_run_id}/timeline"
            )

            assert foreign_response.status_code == 200

            foreign_body = foreign_response.json()

            assert foreign_body == {
                "workflow_run_id": workflow_run_id,
                "status": "not_found",
                "items": [],
            }

    finally:
        app.dependency_overrides.clear()
