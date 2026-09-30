from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.platform.jobs.handlers import (
    JobHandlerRegistry,
)
from app.platform.jobs.repository import (
    JobRepository,
)
from app.platform.jobs.worker import JobWorker


@pytest.mark.asyncio
async def test_failed_handler_does_not_commit_flushed_job_mutation():
    """
    Transaction-boundary proof.

    Application writes performed by a handler must disappear
    when that handler raises.

    This intentionally mutates PlatformJob.result because it gives
    us a durable DB-backed probe without introducing another model.
    """

    job_type = f"test.handler_failure_atomicity.{uuid4()}"

    registry = JobHandlerRegistry()

    async def flush_then_fail(
        payload,
        ctx,
    ):
        del payload

        ctx.job.result = {
            "application_write_that_must_rollback": True,
        }

        # Mirrors commit=False application services:
        # write has reached PostgreSQL transaction state,
        # but must NOT become durable if handler fails.
        await ctx.db.flush()

        raise RuntimeError("intentional failure after application flush")

    registry.register(
        job_type,
        flush_then_fail,
    )

    async with SessionLocal() as db:
        job = await JobRepository(db).enqueue(
            job_type=job_type,
            payload={},
            max_attempts=1,
        )

        job_id = job.id

        processed = await JobWorker(
            db,
            worker_id="failure-atomicity-worker",
            registry=registry,
        ).run_once(
            job_id=job_id,
        )

        assert processed is not None
        assert processed.status == "dead_letter"

    # New session is critical: inspect only durable state.
    async with SessionLocal() as verify_db:
        persisted = await JobRepository(verify_db).get(job_id)

        assert persisted is not None
        assert persisted.status == "dead_letter"

        # Desired invariant:
        # failed handler application mutation must have rolled back.
        assert persisted.result in (
            None,
            {},
        )


@pytest.mark.asyncio
async def test_terminal_failed_handler_rolls_back_writes_and_dead_letters_once():
    job_type = f"test.handler_terminal_failure_atomicity.{uuid4()}"

    registry = JobHandlerRegistry()

    async def flush_then_terminal_fail(
        payload,
        ctx,
    ):
        del payload

        ctx.job.result = {
            "terminal_application_write_must_rollback": True,
        }

        await ctx.db.flush()

        ctx.retryable = False

        raise RuntimeError("intentional terminal handler failure")

    registry.register(
        job_type,
        flush_then_terminal_fail,
    )

    async with SessionLocal() as db:
        job = await JobRepository(db).enqueue(
            job_type=job_type,
            payload={},
            max_attempts=3,
        )

        job_id = job.id

        processed = await JobWorker(
            db,
            worker_id="terminal-atomicity-worker",
            registry=registry,
        ).run_once(
            job_id=job_id,
        )

        assert processed is not None
        assert processed.status == "dead_letter"
        assert processed.attempts == 1
        assert processed.max_attempts == 1

    async with SessionLocal() as verify_db:
        persisted = await JobRepository(verify_db).get(job_id)

        assert persisted is not None
        assert persisted.status == "dead_letter"
        assert persisted.attempts == 1
        assert persisted.max_attempts == 1
        assert persisted.result in (
            None,
            {},
        )
