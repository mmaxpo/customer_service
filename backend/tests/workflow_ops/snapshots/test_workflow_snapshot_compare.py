from uuid import uuid4

import pytest

from app.core.session import get_db
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker
from app.runtime.nodes.registry.builtins import register_builtin_nodes
from app.workflow_operations.diff.snapshot_compare import (
    WorkflowSnapshotCompareService,
)
from app.workflow_operations.snapshots.service import WorkflowSnapshotService


def _workflow():
    return {
        "nodes": [
            {
                "id": "trigger",
                "data": {
                    "nodeType": "trigger.message",
                    "input": "start",
                },
            },
            {
                "id": "set_a",
                "data": {
                    "nodeType": "set.variable",
                    "key": "a",
                    "value": "A",
                },
            },
            {
                "id": "set_b",
                "data": {
                    "nodeType": "set.variable",
                    "key": "b",
                    "value": "B",
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "b",
                },
            },
        ],
        "edges": [
            {
                "id": "e1",
                "source": "trigger",
                "target": "set_a",
            },
            {
                "id": "e2",
                "source": "set_a",
                "target": "set_b",
            },
            {
                "id": "e3",
                "source": "set_b",
                "target": "response",
            },
        ],
    }


@pytest.mark.asyncio
async def test_snapshot_compare_detects_state_changes():

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

        result = await JobWorker(
            db,
            worker_id=f"diff-worker-{uuid4()}",
        ).run_once(job_id=job.id)

        assert result.status == "succeeded"

        workflow_run_id = (
            result.result.get("meta", {}).get("workflow_run_id")
            or result.result.get("workflow_run_id")
            or result.result.get("meta", {}).get("run_id")
        )

        if workflow_run_id is None:
            runs = await JobService(db).repo.list_for_user(
                user_id=user_id,
                limit=10,
            )
            workflow_run_id = (
                result.result.get("meta", {})
                .get("final_state", {})
                .get("workflow_run_id")
            )

        assert workflow_run_id is not None, result.result

        snapshots = await WorkflowSnapshotService(db).list_for_run(
            workflow_run_id=workflow_run_id,
        )

        set_a = next(s for s in snapshots if s.node_id == "set_a")

        set_b = next(s for s in snapshots if s.node_id == "set_b")

        comparison = await WorkflowSnapshotCompareService(
            db,
        ).compare_snapshots(
            before_snapshot_id=set_a.id,
            after_snapshot_id=set_b.id,
        )

        assert comparison["status"] == "ok"

        diff = comparison["diff"]

        assert diff["changed"] is True
        assert diff["vars_changed"]["changed"] is True

        assert "b" in diff["vars_changed"]["added"]

        break
