from uuid import uuid4

import pytest

from app.core.session import get_db
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker
from app.runtime.nodes.registry.builtins import register_builtin_nodes
from app.workflow_operations.diff.run_compare import WorkflowRunCompareService
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
async def test_compare_original_run_to_replay_run():
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

        original_job = await JobWorker(
            db,
            worker_id=f"original-worker-{uuid4()}",
        ).run_once(job_id=job.id)

        assert original_job.status == "succeeded", original_job.error_message
        original_run_id = original_job.result["meta"]["workflow_run_id"]

        snapshots = await WorkflowSnapshotService(db).list_for_run(
            workflow_run_id=original_run_id,
        )

        snapshot = next(
            item
            for item in snapshots
            if item.snapshot_type == "node_end" and item.node_id == "set_a"
        )

        replay = await WorkflowReplayService(db).create_replay_job(
            user_id=user_id,
            snapshot_id=snapshot.id,
        )

        replay_job = await JobWorker(
            db,
            worker_id=f"replay-compare-worker-{uuid4()}",
        ).run_once(job_id=replay["job"].id)

        assert replay_job.status == "succeeded", replay_job.error_message

        replay_run_id = replay_job.result["result"]["meta"]["workflow_run_id"]

        comparison = await WorkflowRunCompareService(db).compare_runs(
            baseline_run_id=original_run_id,
            candidate_run_id=replay_run_id,
        )

        assert comparison["status"] == "ok"
        assert comparison["baseline_run_id"] == original_run_id
        assert comparison["candidate_run_id"] == replay_run_id
        assert comparison["baseline_snapshot_count"] >= 1
        assert comparison["candidate_snapshot_count"] >= 1
        assert "final_state_changed" in comparison
        assert isinstance(comparison["node_output_changes"], list)

        break
