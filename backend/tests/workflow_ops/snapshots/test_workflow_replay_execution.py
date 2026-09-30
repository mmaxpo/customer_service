from uuid import uuid4

import pytest

from app.core.session import get_db
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker
from app.runtime.nodes.registry.builtins import register_builtin_nodes
from app.workflow_operations.snapshots.replay import WorkflowReplayService
from app.workflow_operations.snapshots.service import WorkflowSnapshotService


def _workflow():
    return {
        "nodes": [
            {
                "id": "trigger",
                "data": {"nodeType": "trigger.message", "input": "start"},
            },
            {
                "id": "set_a",
                "data": {"nodeType": "set.variable", "key": "a", "value": "A"},
            },
            {
                "id": "set_b",
                "data": {"nodeType": "set.variable", "key": "b", "value": "B"},
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
            {"id": "e1", "source": "trigger", "target": "set_a"},
            {"id": "e2", "source": "set_a", "target": "set_b"},
            {"id": "e3", "source": "set_b", "target": "response"},
        ],
    }


@pytest.mark.asyncio
async def test_snapshot_replay_executes_from_snapshot_state():
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
            worker_id=f"run-worker-{uuid4()}",
        ).run_once(job_id=job.id)

        assert result_job.status == "succeeded", result_job.error_message
        assert result_job.result["meta"]["status"] == "ok"

        workflow_run_id = result_job.result["meta"]["workflow_run_id"]

        snapshots = await WorkflowSnapshotService(db).list_for_run(
            workflow_run_id=workflow_run_id,
        )

        # Replay from after set_a, so set_b + response should continue.
        snapshot = next(
            s
            for s in snapshots
            if s.snapshot_type == "node_end" and s.node_id == "set_a"
        )

        replay = await WorkflowReplayService(db).create_replay_job(
            user_id=user_id,
            snapshot_id=snapshot.id,
        )

        replay_job = await JobWorker(
            db,
            worker_id=f"replay-worker-{uuid4()}",
        ).run_once(job_id=replay["job"].id)

        assert replay_job.status == "succeeded", replay_job.error_message
        assert replay_job.result["mode"] == "replay_execution"
        assert replay_job.result["replay_supported"] is True
        assert replay_job.result["result"]["meta"]["status"] == "ok", replay_job.result
        assert replay_job.result["result"]["answer"] == "B"

        replay_run_id = replay_job.result["result"]["meta"]["workflow_run_id"]

        assert replay_run_id != workflow_run_id

        break
