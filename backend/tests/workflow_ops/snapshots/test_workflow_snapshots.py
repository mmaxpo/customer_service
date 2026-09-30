from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.core.session import get_db
from app.main import app
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker
from app.runtime.nodes.registry.builtins import register_builtin_nodes
from app.workflow_operations.snapshots.service import WorkflowSnapshotService


class FakeUser:
    def __init__(self):
        self.id = uuid4()


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
                    "value": "SNAPSHOT_OK",
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
async def test_workflow_run_captures_snapshots():
    register_builtin_nodes()
    user_id = uuid4()

    async for db in get_db():
        job = await JobService(db).enqueue(
            user_id=user_id,
            job_type="workflow.run",
            payload={
                "workflow": _workflow(),
                "message": "start",
                "thread_id": str(uuid4()),
            },
        )

        result_job = await JobWorker(
            db,
            worker_id=f"snapshot-worker-{uuid4()}",
        ).run_once(job_id=job.id)

        assert result_job.status == "succeeded", result_job.error_message
        assert result_job.result["meta"]["status"] == "ok"

        workflow_run_id = result_job.result["meta"]["workflow_run_id"]

        snapshots = await WorkflowSnapshotService(db).list_for_run(
            workflow_run_id=workflow_run_id,
        )

        types = [s.snapshot_type for s in snapshots]

        assert "run_start" in types
        assert "node_end" in types
        assert "run_completed" in types

        node_ids = {s.node_id for s in snapshots if s.snapshot_type == "node_end"}

        assert "trigger" in node_ids
        assert "set_result" in node_ids
        assert "response" in node_ids

        assert snapshots[-1].state["last"] == "SNAPSHOT_OK"

        break


@pytest.mark.asyncio
async def test_snapshot_and_diff_routes_reject_foreign_runtime_state():
    owner = FakeUser()
    foreign = FakeUser()

    app.dependency_overrides[get_current_user] = lambda: owner

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            run = await client.post(
                "/workflows_route/run",
                json={
                    "workflow": {
                        "nodes": [
                            {
                                "id": "trigger",
                                "data": {
                                    "nodeType": "trigger.message",
                                },
                            },
                            {
                                "id": "response",
                                "data": {
                                    "nodeType": "response",
                                    "text": "private",
                                },
                            },
                        ],
                        "edges": [
                            {
                                "source": "trigger",
                                "target": "response",
                            }
                        ],
                    },
                    "message": "private",
                    "strict": True,
                },
            )

            assert run.status_code == 200

            run_id = run.json()["meta"]["workflow_run_id"]

            snapshots = await client.get(f"/workflow-snapshots/runs/{run_id}")

            assert snapshots.status_code == 200
            assert snapshots.json()

            snapshot_id = snapshots.json()[0]["id"]

            app.dependency_overrides[get_current_user] = lambda: foreign

            foreign_list = await client.get(f"/workflow-snapshots/runs/{run_id}")
            assert foreign_list.status_code == 200
            assert foreign_list.json() == []

            foreign_get = await client.get(f"/workflow-snapshots/{snapshot_id}")
            assert foreign_get.status_code == 404

            foreign_replay = await client.post(
                f"/workflow-snapshots/{snapshot_id}/replay"
            )
            assert foreign_replay.status_code == 404

            foreign_compare = await client.get(
                "/workflow-diff/snapshots/compare",
                params={
                    "before_snapshot_id": snapshot_id,
                    "after_snapshot_id": snapshot_id,
                },
            )
            assert foreign_compare.status_code == 404

            foreign_run_compare = await client.get(
                "/workflow-diff/runs/compare",
                params={
                    "baseline_run_id": run_id,
                    "candidate_run_id": run_id,
                },
            )
            assert foreign_run_compare.status_code == 404

    finally:
        app.dependency_overrides.clear()
