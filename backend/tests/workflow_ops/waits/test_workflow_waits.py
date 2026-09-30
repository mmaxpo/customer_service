from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.core.session import get_db
from app.main import app
from app.platform.jobs.service import JobService
from app.workflow_operations.waits.scheduler import WorkflowWaitScheduler
from app.workflow_operations.waits.schemas import WorkflowWaitCreate
from app.workflow_operations.waits.service import WorkflowWaitService


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_workflow_wait_api_create_and_resolve_enqueues_resume_job():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/workflow-waits",
                json={
                    "workflow_run_id": "run-1",
                    "node_id": "approval-1",
                    "wait_type": "approval",
                    "payload": {"question": "Approve?"},
                },
            )

            assert created.status_code == 200
            wait = created.json()
            assert wait["status"] == "waiting"

            resolved = await client.post(
                f"/workflow-waits/{wait['id']}/resolve",
                json={
                    "resolution": {"approved": True},
                    "resume": True,
                },
            )

            assert resolved.status_code == 200
            body = resolved.json()

            assert body["wait"]["status"] == "resolved"
            assert body["wait"]["resolution"]["approved"] is True
            assert body["resume_job_id"] is not None

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_expired_wait_enqueues_resume_job():
    user_id = uuid4()

    async for db in get_db():
        wait = await WorkflowWaitService(db).create(
            user_id=user_id,
            payload=WorkflowWaitCreate(
                workflow_run_id="run-expire",
                node_id="wait-1",
                wait_type="time",
                payload={"reason": "delay"},
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            ),
        )

        expired = await WorkflowWaitScheduler(db).expire_due()

        item = next(w for w in expired if w.id == wait.id)

        assert item.status == "expired"
        assert item.resolution["expired"] is True

        jobs = await JobService(db).repo.list_for_user(
            user_id=user_id,
            limit=20,
        )

        assert any(
            job.job_type == "workflow.resume"
            and job.payload["workflow_run_id"] == "run-expire"
            for job in jobs
        )

        break


@pytest.mark.asyncio
async def test_expire_due_http_is_scoped_to_current_user():
    caller = FakeUser()
    other_user_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: caller

    try:
        async for db in get_db():
            caller_wait = await WorkflowWaitService(db).create(
                user_id=caller.id,
                payload=WorkflowWaitCreate(
                    workflow_run_id="run-expire-http-caller",
                    node_id="wait-caller",
                    wait_type="time",
                    payload={"owner": "caller"},
                    expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
                ),
            )

            other_wait = await WorkflowWaitService(db).create(
                user_id=other_user_id,
                payload=WorkflowWaitCreate(
                    workflow_run_id="run-expire-http-other",
                    node_id="wait-other",
                    wait_type="time",
                    payload={"owner": "other"},
                    expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
                ),
            )

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post("/workflow-waits/expire-due")

            assert response.status_code == 200
            expired = response.json()

            caller_wait_id = caller_wait.id
            other_wait_id = other_wait.id

            expired_ids = {item["id"] for item in expired}
            assert str(caller_wait_id) in expired_ids
            assert str(other_wait_id) not in expired_ids

            # The HTTP request uses its own database session. Expire objects
            # loaded by this setup session so the verification queries observe
            # the committed state produced by the request.
            db.expire_all()

            caller_saved = await WorkflowWaitService(db).get_for_user(
                user_id=caller.id,
                wait_id=caller_wait_id,
            )
            other_saved = await WorkflowWaitService(db).get_for_user(
                user_id=other_user_id,
                wait_id=other_wait_id,
            )

            assert caller_saved.status == "expired"
            assert caller_saved.resolution["expired"] is True

            assert other_saved.status == "waiting"
            assert other_saved.resolution is None
            assert other_saved.resolved_at is None

            break

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_background_wait_scheduler_remains_global():
    first_user_id = uuid4()
    second_user_id = uuid4()

    async for db in get_db():
        first_wait = await WorkflowWaitService(db).create(
            user_id=first_user_id,
            payload=WorkflowWaitCreate(
                workflow_run_id="run-global-expire-first",
                node_id="wait-first",
                wait_type="time",
                payload={},
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            ),
        )

        second_wait = await WorkflowWaitService(db).create(
            user_id=second_user_id,
            payload=WorkflowWaitCreate(
                workflow_run_id="run-global-expire-second",
                node_id="wait-second",
                wait_type="time",
                payload={},
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            ),
        )

        expired = await WorkflowWaitScheduler(db).expire_due()
        expired_ids = {item.id for item in expired}

        assert first_wait.id in expired_ids
        assert second_wait.id in expired_ids

        break
