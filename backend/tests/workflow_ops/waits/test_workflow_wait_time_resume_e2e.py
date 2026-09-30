from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import get_db
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker
from app.runtime.nodes.registry.builtins import register_builtin_nodes
from app.workflow_operations.waits.scheduler import WorkflowWaitScheduler
from app.workflow_operations.waits.service import WorkflowWaitService


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
                "id": "wait",
                "data": {
                    "nodeType": "wait.time",
                    "seconds": 3600,
                    "reason": "test wake",
                },
            },
            {
                "id": "set_result",
                "data": {
                    "nodeType": "set.variable",
                    "key": "result",
                    "value": "DONE_AFTER_WAIT",
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
            {"id": "e1", "source": "trigger", "target": "wait"},
            {"id": "e2", "source": "wait", "target": "set_result"},
            {"id": "e3", "source": "set_result", "target": "response"},
        ],
    }


@pytest.mark.asyncio
async def test_wait_time_scheduler_resume_job_completes_workflow():
    register_builtin_nodes()
    user_id = uuid4()

    async for db in get_db():
        start_job = await JobService(db).enqueue(
            user_id=user_id,
            job_type="workflow.run",
            payload={
                "workflow": _workflow(),
                "message": "start",
                "thread_id": str(uuid4()),
            },
        )

        started_job = await JobWorker(
            db,
            worker_id=f"start-worker-{uuid4()}",
        ).run_once(job_id=start_job.id)

        assert started_job.status == "succeeded", started_job.error_message
        assert started_job.result["meta"]["status"] == "paused", started_job.result

        workflow_run_id = started_job.result["meta"]["workflow_run_id"]

        waits = await WorkflowWaitService(db).list_for_user(
            user_id=user_id,
            status="waiting",
        )

        wait = next(item for item in waits if item.workflow_run_id == workflow_run_id)

        wait.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await WorkflowWaitService(db).repo.save(wait)

        expired = await WorkflowWaitScheduler(
            db,
            worker_id="test-wait-scheduler",
        ).wake_due_time_waits()

        assert any(item.id == wait.id for item in expired)

        jobs = await JobService(db).repo.list_for_user(
            user_id=user_id,
            limit=50,
        )

        resume_job = next(
            job
            for job in jobs
            if job.job_type == "workflow.resume"
            and job.payload["workflow_run_id"] == workflow_run_id
        )

        result_job = await JobWorker(
            db,
            worker_id=f"resume-worker-{uuid4()}",
        ).run_once(job_id=resume_job.id)

        assert result_job.status == "succeeded", result_job.error_message
        assert result_job.result["meta"]["status"] == "ok", result_job.result
        assert result_job.result["answer"] == "DONE_AFTER_WAIT"

        break
