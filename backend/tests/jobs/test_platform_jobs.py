from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.core.session import get_db
from app.main import app
from app.platform.jobs.handlers import JobHandlerRegistry
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_jobs_api_enqueue_and_list():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/jobs",
                json={
                    "job_type": "test.echo",
                    "payload": {"hello": "world"},
                },
            )

            assert created.status_code == 200
            assert created.json()["status"] == "queued"

            listed = await client.get("/jobs")

            assert listed.status_code == 200
            assert any(job["id"] == created.json()["id"] for job in listed.json())

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_job_worker_runs_echo_job():
    user_id = uuid4()
    job_type = f"test.echo.{uuid4()}"

    registry = JobHandlerRegistry()

    async def handler(payload):
        return {"echo": payload}

    registry.register(job_type, handler)

    async for db in get_db():
        job = await JobService(db).enqueue(
            user_id=user_id,
            job_type=job_type,
            payload={"hello": "worker"},
        )

        result = await JobWorker(
            db,
            worker_id=f"test-worker-{uuid4()}",
            registry=registry,
        ).run_once()

        assert result is not None
        assert result.id == job.id
        assert result.status == "succeeded"
        assert result.result == {"echo": {"hello": "worker"}}

        break
