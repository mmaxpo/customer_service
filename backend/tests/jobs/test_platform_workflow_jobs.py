from uuid import uuid4

import pytest

from app.core.session import get_db
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker


def _simple_workflow():
    return {
        "nodes": [
            {
                "id": "t1",
                "data": {
                    "nodeType": "trigger.message",
                    "input": "start",
                },
            },
            {
                "id": "s1",
                "data": {
                    "nodeType": "set.variable",
                    "key": "job_result",
                    "value": "OK",
                },
            },
            {
                "id": "r1",
                "data": {
                    "nodeType": "response",
                },
            },
        ],
        "edges": [
            {
                "id": "e1",
                "source": "t1",
                "target": "s1",
            },
            {
                "id": "e2",
                "source": "s1",
                "target": "r1",
            },
        ],
    }


def _approval_workflow():
    return {
        "nodes": [
            {
                "id": "t1",
                "data": {
                    "nodeType": "trigger.message",
                    "input": "start",
                },
            },
            {
                "id": "h1",
                "data": {
                    "nodeType": "human.approval",
                    "question": "Approve?",
                    "save_as": "approved",
                },
            },
            {
                "id": "s1",
                "data": {
                    "nodeType": "set.variable",
                    "key": "after_resume",
                    "value": "DONE",
                },
            },
            {
                "id": "r1",
                "data": {
                    "nodeType": "response",
                },
            },
        ],
        "edges": [
            {
                "id": "e1",
                "source": "t1",
                "target": "h1",
            },
            {
                "id": "e2",
                "source": "h1",
                "target": "s1",
            },
            {
                "id": "e3",
                "source": "s1",
                "target": "r1",
            },
        ],
    }


@pytest.mark.asyncio
async def test_workflow_run_job_executes_workflow():
    user_id = uuid4()

    async for db in get_db():
        job = await JobService(db).enqueue(
            user_id=user_id,
            job_type="workflow.run",
            payload={
                "workflow": _simple_workflow(),
                "message": "hello",
                "thread_id": str(uuid4()),
            },
        )

        result = await JobWorker(
            db,
            worker_id=f"workflow-worker-{uuid4()}",
        ).run_once(job_id=job.id)

        assert result is not None
        assert result.id == job.id
        assert result.status == "succeeded"
        assert result.result["meta"]["status"] == "ok"
        assert result.result["meta"]["final_state"]["vars"]["job_result"] == "OK"

        break


@pytest.mark.asyncio
async def test_workflow_resume_job_resumes_paused_workflow():
    user_id = uuid4()

    async for db in get_db():
        start_job = await JobService(db).enqueue(
            user_id=user_id,
            job_type="workflow.run",
            payload={
                "workflow": _approval_workflow(),
                "message": "hello",
                "thread_id": str(uuid4()),
            },
        )

        started = await JobWorker(
            db,
            worker_id=f"workflow-worker-{uuid4()}",
        ).run_once(job_id=start_job.id)

        assert started.id == start_job.id
        assert started.status == "succeeded"
        assert started.result["meta"]["status"] == "paused"

        workflow_run_id = started.result["meta"]["workflow_run_id"]

        resume_job = await JobService(db).enqueue(
            user_id=user_id,
            job_type="workflow.resume",
            payload={
                "workflow_run_id": workflow_run_id,
                "input": {
                    "approved": True,
                },
            },
        )

        resumed = await JobWorker(
            db,
            worker_id=f"workflow-worker-{uuid4()}",
        ).run_once(job_id=resume_job.id)

        assert resumed.id == resume_job.id
        assert resumed.status == "succeeded"
        assert resumed.result["meta"]["status"] == "ok"
        assert resumed.result["meta"]["final_state"]["vars"]["approved"] is True
        assert resumed.result["meta"]["final_state"]["vars"]["after_resume"] == "DONE"

        break
