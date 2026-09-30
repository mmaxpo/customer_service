from uuid import uuid4

import pytest

from app.core.session import get_db
from app.platform.jobs.dead_letter import DeadLetterRepository
from app.platform.jobs.handlers import JobHandlerRegistry
from app.platform.jobs.replay import JobReplayService
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker


@pytest.mark.asyncio
async def test_failed_job_moves_to_dead_letter_after_max_attempts():
    user_id = uuid4()
    job_type = f"test.fail.{uuid4()}"

    registry = JobHandlerRegistry()

    async def handler(payload, ctx):
        raise RuntimeError("boom")

    registry.register(job_type, handler)

    async for db in get_db():
        job = await JobService(db).enqueue(
            user_id=user_id,
            job_type=job_type,
            payload={"x": 1},
            max_attempts=1,
        )

        result = await JobWorker(
            db,
            worker_id=f"worker-{uuid4()}",
            registry=registry,
        ).run_once(job_id=job.id)

        assert result.status == "dead_letter"
        assert result.error_message == "boom"

        dead_letters = await DeadLetterRepository(db).list_for_user(
            user_id=user_id,
        )

        dead = next(item for item in dead_letters if item.job_id == job.id)

        assert dead.job_type == job_type
        assert dead.error_message == "boom"
        assert dead.status == "dead"

        break


@pytest.mark.asyncio
async def test_replay_dead_letter_creates_new_job():
    user_id = uuid4()
    job_type = f"test.fail.{uuid4()}"

    registry = JobHandlerRegistry()

    async def handler(payload, ctx):
        raise RuntimeError("boom")

    registry.register(job_type, handler)

    async for db in get_db():
        job = await JobService(db).enqueue(
            user_id=user_id,
            job_type=job_type,
            payload={"x": 1},
            max_attempts=1,
        )

        await JobWorker(
            db,
            worker_id=f"worker-{uuid4()}",
            registry=registry,
        ).run_once(job_id=job.id)

        dead_letters = await DeadLetterRepository(db).list_for_user(
            user_id=user_id,
        )

        dead = next(item for item in dead_letters if item.job_id == job.id)

        replayed = await JobReplayService(db).replay_dead_letter(
            user_id=user_id,
            dead_letter_id=dead.id,
        )

        assert replayed.id != job.id
        assert replayed.job_type == job_type
        assert replayed.payload["original_job_id"] == str(job.id)
        assert replayed.payload["replayed_from_dead_letter_id"] == str(dead.id)

        refreshed_dead = await DeadLetterRepository(db).get(dead.id)
        assert refreshed_dead.status == "replayed"

        break
