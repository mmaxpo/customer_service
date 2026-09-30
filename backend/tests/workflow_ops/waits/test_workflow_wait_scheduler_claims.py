from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import get_db
from app.platform.jobs.service import JobService
from app.workflow_operations.waits.repository import WorkflowWaitRepository
from app.workflow_operations.waits.scheduler import WorkflowWaitScheduler
from app.workflow_operations.waits.schemas import WorkflowWaitCreate
from app.workflow_operations.waits.service import WorkflowWaitService


@pytest.mark.asyncio
async def test_wait_scheduler_claims_due_time_wait_and_enqueues_resume_job():
    user_id = uuid4()

    async for db in get_db():
        wait = await WorkflowWaitService(db).create(
            user_id=user_id,
            payload=WorkflowWaitCreate(
                workflow_run_id="run-claim-1",
                node_id="wait-1",
                wait_type="time",
                payload={"seconds": 1},
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            ),
        )

        expired = await WorkflowWaitScheduler(
            db,
            worker_id="scheduler-1",
        ).wake_due_time_waits()

        saved = next(item for item in expired if item.id == wait.id)

        assert saved.status == "expired"
        assert saved.claimed_by == "scheduler-1"
        assert saved.claimed_at is not None

        jobs = await JobService(db).repo.list_for_user(
            user_id=user_id,
            limit=20,
        )

        resume_job = next(
            job
            for job in jobs
            if job.job_type == "workflow.resume"
            and job.payload["workflow_run_id"] == "run-claim-1"
        )

        assert resume_job.payload["input"]["expired"] is True
        assert resume_job.payload["input"]["wait_id"] == str(wait.id)

        break


@pytest.mark.asyncio
async def test_claim_due_time_waits_is_idempotent_after_first_claim():
    user_id = uuid4()

    async for db in get_db():
        wait = await WorkflowWaitService(db).create(
            user_id=user_id,
            payload=WorkflowWaitCreate(
                workflow_run_id="run-claim-2",
                node_id="wait-2",
                wait_type="time",
                payload={},
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            ),
        )

        first = await WorkflowWaitRepository(db).claim_due_time_waits(
            worker_id="worker-a",
        )

        assert any(item.id == wait.id for item in first)

        second = await WorkflowWaitRepository(db).claim_due_time_waits(
            worker_id="worker-b",
        )

        assert all(item.id != wait.id for item in second)

        break
