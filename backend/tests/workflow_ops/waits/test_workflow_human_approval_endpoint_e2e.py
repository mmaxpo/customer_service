from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.core.session import get_db
from app.main import app
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker
from app.runtime.nodes.registry.builtins import register_builtin_nodes
from app.workflow_operations.waits.service import WorkflowWaitService


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "approval@test.com"


def _workflow():
    return {
        "nodes": [
            {
                "id": "trigger",
                "data": {"nodeType": "trigger.message", "input": "start"},
            },
            {
                "id": "approval",
                "data": {
                    "nodeType": "human.approval",
                    "question": "Approve refund?",
                    "save_as": "approved",
                },
            },
            {
                "id": "set_result",
                "data": {
                    "nodeType": "set.variable",
                    "key": "result",
                    "value": "APPROVED_DONE",
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
            {"id": "e1", "source": "trigger", "target": "approval"},
            {"id": "e2", "source": "approval", "target": "set_result"},
            {"id": "e3", "source": "set_result", "target": "response"},
        ],
    }


@pytest.mark.asyncio
async def test_approve_workflow_wait_endpoint_resumes_workflow():
    register_builtin_nodes()

    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            async for db in get_db():
                start_job = await JobService(db).enqueue(
                    user_id=user.id,
                    job_type="workflow.run",
                    payload={
                        "workflow": _workflow(),
                        "message": "start",
                        "thread_id": str(uuid4()),
                    },
                )

                started_job = await JobWorker(
                    db,
                    worker_id=f"approval-start-worker-{uuid4()}",
                ).run_once(job_id=start_job.id)

                assert started_job.status == "succeeded", started_job.error_message
                assert started_job.result["meta"]["status"] == "paused", (
                    started_job.result
                )

                workflow_run_id = started_job.result["meta"]["workflow_run_id"]

                waits = await WorkflowWaitService(db).list_for_user(
                    user_id=user.id,
                    status="waiting",
                )

                wait = next(
                    item for item in waits if item.workflow_run_id == workflow_run_id
                )

                approval = await client.post(f"/workflow-waits/{wait.id}/approve")

                assert approval.status_code == 200, approval.text

                approval_body = approval.json()

                assert approval_body["approved"] is True
                assert approval_body["status"] == "resolved"
                assert approval_body["resume_job_id"]

                resumed_job = await JobWorker(
                    db,
                    worker_id=f"approval-resume-worker-{uuid4()}",
                ).run_once(job_id=UUID(approval_body["resume_job_id"]))

                assert resumed_job.status == "succeeded", resumed_job.error_message
                assert resumed_job.result["meta"]["status"] == "ok", resumed_job.result
                assert resumed_job.result["answer"] == "APPROVED_DONE"

                break

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reject_workflow_wait_endpoint_resumes_workflow():
    register_builtin_nodes()

    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            async for db in get_db():
                start_job = await JobService(db).enqueue(
                    user_id=user.id,
                    job_type="workflow.run",
                    payload={
                        "workflow": _workflow(),
                        "message": "start",
                        "thread_id": str(uuid4()),
                    },
                )

                started_job = await JobWorker(
                    db,
                    worker_id=f"reject-start-worker-{uuid4()}",
                ).run_once(job_id=start_job.id)

                assert started_job.status == "succeeded", started_job.error_message
                assert started_job.result["meta"]["status"] == "paused", (
                    started_job.result
                )

                workflow_run_id = started_job.result["meta"]["workflow_run_id"]

                waits = await WorkflowWaitService(db).list_for_user(
                    user_id=user.id,
                    status="waiting",
                )

                wait = next(
                    item for item in waits if item.workflow_run_id == workflow_run_id
                )

                rejection = await client.post(f"/workflow-waits/{wait.id}/reject")

                assert rejection.status_code == 200, rejection.text

                rejection_body = rejection.json()

                assert rejection_body["approved"] is False
                assert rejection_body["status"] == "resolved"
                assert rejection_body["resume_job_id"]

                resumed_job = await JobWorker(
                    db,
                    worker_id=f"reject-resume-worker-{uuid4()}",
                ).run_once(job_id=UUID(rejection_body["resume_job_id"]))

                assert resumed_job.status == "succeeded", resumed_job.error_message
                assert resumed_job.result["meta"]["status"] == "ok", resumed_job.result
                assert resumed_job.result["answer"] == "APPROVED_DONE"

                break

    finally:
        app.dependency_overrides.clear()
