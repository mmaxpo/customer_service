from uuid import uuid4

import pytest

from app.core.session import get_db
from app.platform.events.publisher import PlatformEventPublisher
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker
from app.runtime.nodes.registry.builtins import register_builtin_nodes
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
                "id": "wait_event",
                "data": {
                    "nodeType": "wait.event",
                    "event_type": "shopify.order.updated",
                    "match": {
                        "order_id": "1001",
                    },
                    "reason": "wait for order update",
                },
            },
            {
                "id": "set_result",
                "data": {
                    "nodeType": "set.variable",
                    "key": "result",
                    "value": "EVENT_RECEIVED",
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
            {"id": "e1", "source": "trigger", "target": "wait_event"},
            {"id": "e2", "source": "wait_event", "target": "set_result"},
            {"id": "e3", "source": "set_result", "target": "response"},
        ],
    }


@pytest.mark.asyncio
async def test_wait_event_resolves_from_platform_event_and_resumes_workflow():
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

        assert wait.wait_type == "event"
        assert wait.payload["event_type"] == "shopify.order.updated"

        publish_result = await PlatformEventPublisher(db).publish(
            user_id=user_id,
            event_type="shopify.order.updated",
            source="shopify",
            payload={
                "order_id": "1001",
                "status": "fulfilled",
            },
        )

        handler_results = publish_result["handler_results"]
        assert any(
            str(wait.id) in item.get("resolved_wait_ids", [])
            for item in handler_results
        )

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
        assert result_job.result["answer"] == "EVENT_RECEIVED"

        break
