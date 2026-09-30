from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import get_db
from app.platform.jobs.handlers import JobHandlerRegistry
from app.platform.jobs.metrics import JobMetricsService
from app.platform.jobs.recovery import JobRecoveryService
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker


@pytest.mark.asyncio
async def test_job_claim_sets_heartbeat_and_success_clears_lock():
    user_id = uuid4()
    job_type = f"test.heartbeat.{uuid4()}"

    registry = JobHandlerRegistry()

    async def handler(payload, ctx):
        return {"ok": True}

    registry.register(job_type, handler)

    async for db in get_db():
        job = await JobService(db).enqueue(
            user_id=user_id,
            job_type=job_type,
            payload={},
        )

        result = await JobWorker(
            db,
            worker_id="heartbeat-worker",
            registry=registry,
        ).run_once(job_id=job.id)

        assert result.status == "succeeded"
        assert result.locked_at is None
        assert result.locked_by is None
        assert result.heartbeat_at is None

        break


@pytest.mark.asyncio
async def test_recover_abandoned_running_job_requeues_it():
    user_id = uuid4()
    job_type = f"test.recover.{uuid4()}"

    async for db in get_db():
        job = await JobService(db).enqueue(
            user_id=user_id,
            job_type=job_type,
            payload={},
            max_attempts=3,
        )

        claimed = await JobWorker(
            db,
            worker_id="claimer",
            registry=JobHandlerRegistry(),
        ).repo.claim_next_due(
            worker_id="claimer",
            job_types={job_type},
            job_id=job.id,
        )

        assert claimed.status == "running"

        claimed.locked_at = datetime.now(timezone.utc) - timedelta(seconds=999)
        await db.commit()
        await db.refresh(claimed)

        recovered = await JobRecoveryService(
            db,
            lease_seconds=1,
        ).recover_abandoned()

        recovered_job = next(item for item in recovered if item.id == job.id)

        assert recovered_job.status == "queued"
        assert recovered_job.locked_at is None
        assert recovered_job.locked_by is None

        break


@pytest.mark.asyncio
async def test_job_metrics_counts_statuses():
    user_id = uuid4()
    job_type = f"test.metrics.{uuid4()}"

    async for db in get_db():
        await JobService(db).enqueue(
            user_id=user_id,
            job_type=job_type,
            payload={},
        )

        metrics = JobMetricsService(db)

        assert await metrics.queue_depth() >= 1

        by_status = await metrics.counts_by_status()
        by_type = await metrics.counts_by_type()

        assert by_status["queued"] >= 1
        assert by_type[job_type] >= 1

        break


@pytest.mark.asyncio
async def test_worker_failure_survives_handler_session_rollback():
    from app.core.session import SessionLocal
    from app.platform.jobs.handlers import JobHandlerRegistry
    from app.platform.jobs.repository import JobRepository
    from app.platform.jobs.worker import JobWorker

    async with SessionLocal() as db:
        registry = JobHandlerRegistry()

        async def rollback_then_fail(payload, ctx):
            del payload
            await ctx.db.rollback()
            raise RuntimeError("expected handler failure after rollback")

        registry.register(
            "test.rollback_then_fail",
            rollback_then_fail,
        )

        job = await JobRepository(db).enqueue(
            job_type="test.rollback_then_fail",
            payload={},
            max_attempts=1,
        )

        job_id = job.id

        result = await JobWorker(
            db,
            worker_id="test-worker",
            registry=registry,
        ).run_once(job_id=job_id)

        assert result is not None
        assert result.id == job_id
        assert result.status == "dead_letter"
        assert result.attempts == 1
        assert result.error_message == "expected handler failure after rollback"

        persisted = await JobRepository(db).get(job_id)

        assert persisted is not None
        assert persisted.status == "dead_letter"
        assert persisted.attempts == 1


@pytest.mark.asyncio
async def test_job_service_get_rejects_cross_user_access():
    from uuid import uuid4

    from fastapi import HTTPException

    from app.core.session import get_db
    from app.platform.jobs.service import JobService

    owner_id = uuid4()
    attacker_id = uuid4()

    async for db in get_db():
        service = JobService(db)

        job = await service.enqueue(
            user_id=owner_id,
            job_type=f"test.isolation.{uuid4()}",
            payload={
                "secret_marker": "owner-private-job",
            },
        )

        owner_view = await service.get(
            job_id=job.id,
            user_id=owner_id,
        )

        assert owner_view.id == job.id
        assert owner_view.user_id == owner_id

        with pytest.raises(HTTPException) as exc_info:
            await service.get(
                job_id=job.id,
                user_id=attacker_id,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Job not found"

        break


@pytest.mark.asyncio
async def test_job_metrics_can_scope_counts_to_user():
    from uuid import uuid4

    from app.core.session import get_db
    from app.platform.jobs.metrics import JobMetricsService
    from app.platform.jobs.service import JobService

    user_a = uuid4()
    user_b = uuid4()
    job_type = f"test.metrics.isolation.{uuid4()}"

    async for db in get_db():
        jobs = JobService(db)

        await jobs.enqueue(
            user_id=user_a,
            job_type=job_type,
            payload={},
        )

        metrics = JobMetricsService(db)

        a_counts = await metrics.counts_by_type(
            user_id=user_a,
        )
        b_counts = await metrics.counts_by_type(
            user_id=user_b,
        )

        assert a_counts[job_type] == 1
        assert job_type not in b_counts

        # Internal/global behavior remains available.
        global_counts = await metrics.counts_by_type()
        assert global_counts[job_type] >= 1

        break


@pytest.mark.asyncio
async def test_job_recovery_can_scope_abandoned_jobs_to_user():
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    from app.core.session import get_db
    from app.platform.jobs.recovery import JobRecoveryService
    from app.platform.jobs.service import JobService

    user_a = uuid4()
    user_b = uuid4()
    old = datetime.now(timezone.utc) - timedelta(hours=1)

    async for db in get_db():
        service = JobService(db)

        job_a = await service.enqueue(
            user_id=user_a,
            job_type=f"test.recover.a.{uuid4()}",
            payload={},
        )
        job_b = await service.enqueue(
            user_id=user_b,
            job_type=f"test.recover.b.{uuid4()}",
            payload={},
        )

        for job in (job_a, job_b):
            job.status = "running"
            job.attempts = 1
            job.locked_by = "abandoned-worker"
            job.locked_at = old
            job.heartbeat_at = old

        await db.commit()
        await db.refresh(job_a)
        await db.refresh(job_b)

        recovered = await JobRecoveryService(
            db,
            lease_seconds=1,
        ).recover_abandoned(
            user_id=user_b,
        )

        assert {job.id for job in recovered} == {job_b.id}

        await db.refresh(job_a)
        await db.refresh(job_b)

        assert job_a.status == "running"
        assert job_a.locked_by == "abandoned-worker"

        assert job_b.status == "queued"
        assert job_b.locked_by is None

        break


@pytest.mark.asyncio
async def test_recovery_retryable_job_does_not_create_dead_letter():
    from app.platform.jobs.dead_letter import DeadLetterRepository

    user_id = uuid4()
    job_type = f"test.recovery.retryable.{uuid4()}"
    old = datetime.now(timezone.utc) - timedelta(hours=1)

    async for db in get_db():
        job = await JobService(db).enqueue(
            user_id=user_id,
            job_type=job_type,
            payload={"kind": "retryable"},
            max_attempts=3,
        )

        claimed = await JobWorker(
            db,
            worker_id="recovery-retryable-worker",
            registry=JobHandlerRegistry(),
        ).repo.claim_next_due(
            worker_id="recovery-retryable-worker",
            job_types={job_type},
            job_id=job.id,
        )

        assert claimed is not None
        assert claimed.status == "running"
        assert claimed.attempts == 1

        claimed.locked_at = old
        claimed.heartbeat_at = old

        await db.commit()

        recovered = await JobRecoveryService(
            db,
            lease_seconds=1,
        ).recover_abandoned(
            user_id=user_id,
        )

        recovered_job = next(item for item in recovered if item.id == job.id)

        assert recovered_job.status == "queued"
        assert recovered_job.error_message == ("Recovered abandoned running job")

        dead_letters = await DeadLetterRepository(db).list_for_user(
            user_id=user_id,
        )

        assert all(item.job_id != job.id for item in dead_letters)

        break


@pytest.mark.asyncio
async def test_recovery_terminal_job_creates_replayable_dead_letter():
    from app.platform.jobs.dead_letter import DeadLetterRepository
    from app.platform.jobs.replay import JobReplayService

    user_id = uuid4()
    job_type = f"test.recovery.dead-letter.{uuid4()}"
    old = datetime.now(timezone.utc) - timedelta(hours=1)

    async for db in get_db():
        job = await JobService(db).enqueue(
            user_id=user_id,
            job_type=job_type,
            payload={
                "kind": "terminal-recovery",
                "marker": "CORE-3.6C",
            },
            max_attempts=1,
        )

        claimed = await JobWorker(
            db,
            worker_id="recovery-terminal-worker",
            registry=JobHandlerRegistry(),
        ).repo.claim_next_due(
            worker_id="recovery-terminal-worker",
            job_types={job_type},
            job_id=job.id,
        )

        assert claimed is not None
        assert claimed.status == "running"
        assert claimed.attempts == 1
        assert claimed.max_attempts == 1

        claimed.locked_at = old
        claimed.heartbeat_at = old

        await db.commit()

        recovered = await JobRecoveryService(
            db,
            lease_seconds=1,
        ).recover_abandoned(
            user_id=user_id,
        )

        matches = [item for item in recovered if item.id == job.id]

        assert len(matches) == 1

        recovered_job = matches[0]

        assert recovered_job.status == "dead_letter"
        assert recovered_job.attempts == 1
        assert recovered_job.finished_at is not None
        assert recovered_job.locked_at is None
        assert recovered_job.locked_by is None
        assert recovered_job.error_message == ("Recovered abandoned running job")

        dead_letters = await DeadLetterRepository(db).list_for_user(
            user_id=user_id,
        )

        matches = [item for item in dead_letters if item.job_id == job.id]

        assert len(matches) == 1

        dead = matches[0]

        assert dead.user_id == user_id
        assert dead.job_type == job_type
        assert dead.payload == {
            "kind": "terminal-recovery",
            "marker": "CORE-3.6C",
        }
        assert dead.error_message == ("Recovered abandoned running job")
        assert dead.attempts == 1
        assert dead.status == "dead"

        replayed = await JobReplayService(db).replay_dead_letter(
            user_id=user_id,
            dead_letter_id=dead.id,
        )

        assert replayed.id != job.id
        assert replayed.user_id == user_id
        assert replayed.job_type == job_type
        assert replayed.status == "queued"
        assert replayed.attempts == 0
        assert replayed.max_attempts == 3

        assert replayed.payload["marker"] == "CORE-3.6C"
        assert replayed.payload["original_job_id"] == str(job.id)
        assert replayed.payload["replayed_from_dead_letter_id"] == str(dead.id)

        refreshed_dead = await DeadLetterRepository(db).get(dead.id)

        assert refreshed_dead is not None
        assert refreshed_dead.status == "replayed"

        break


@pytest.mark.asyncio
async def test_recovery_terminal_job_emits_dead_letter_event():
    from sqlalchemy import select

    from app.models.models import PlatformDeadLetter, PlatformEvent

    user_id = uuid4()
    job_type = f"test.recovery.dead-letter-event.{uuid4()}"
    old = datetime.now(timezone.utc) - timedelta(hours=1)

    async for db in get_db():
        job = await JobService(db).enqueue(
            user_id=user_id,
            job_type=job_type,
            payload={
                "marker": "CORE-3.7D",
            },
            max_attempts=1,
        )

        claimed = await JobWorker(
            db,
            worker_id="recovery-event-worker",
            registry=JobHandlerRegistry(),
        ).repo.claim_next_due(
            worker_id="recovery-event-worker",
            job_types={job_type},
            job_id=job.id,
        )

        assert claimed is not None
        assert claimed.status == "running"
        assert claimed.attempts == 1
        assert claimed.max_attempts == 1

        claimed.locked_at = old
        claimed.heartbeat_at = old

        await db.commit()

        recovered = await JobRecoveryService(
            db,
            lease_seconds=1,
        ).recover_abandoned(
            user_id=user_id,
        )

        recovered_job = next(item for item in recovered if item.id == job.id)

        assert recovered_job.status == "dead_letter"

        dead = (
            await db.execute(
                select(PlatformDeadLetter).where(
                    PlatformDeadLetter.job_id == job.id,
                )
            )
        ).scalar_one()

        events = list(
            (
                await db.execute(
                    select(PlatformEvent).where(
                        PlatformEvent.user_id == user_id,
                        PlatformEvent.event_type == "job.dead_lettered",
                    )
                )
            )
            .scalars()
            .all()
        )

        matching = [
            event
            for event in events
            if (event.payload or {}).get("job_id") == str(job.id)
        ]

        assert len(matching) == 1

        event = matching[0]

        assert event.source == "jobs"
        assert event.status == "published"

        assert event.payload == {
            "job_id": str(job.id),
            "dead_letter_id": str(dead.id),
            "job_type": job_type,
            "attempts": 1,
            "error_message": ("Recovered abandoned running job"),
        }

        break


@pytest.mark.asyncio
async def test_retryable_recovery_emits_no_dead_letter_event():
    from sqlalchemy import select

    from app.models.models import PlatformEvent

    user_id = uuid4()
    job_type = f"test.recovery.no-dead-letter-event.{uuid4()}"
    old = datetime.now(timezone.utc) - timedelta(hours=1)

    async for db in get_db():
        job = await JobService(db).enqueue(
            user_id=user_id,
            job_type=job_type,
            payload={
                "marker": "CORE-3.7D-retryable",
            },
            max_attempts=3,
        )

        claimed = await JobWorker(
            db,
            worker_id="recovery-retryable-event-worker",
            registry=JobHandlerRegistry(),
        ).repo.claim_next_due(
            worker_id="recovery-retryable-event-worker",
            job_types={job_type},
            job_id=job.id,
        )

        assert claimed is not None
        assert claimed.status == "running"
        assert claimed.attempts == 1

        claimed.locked_at = old
        claimed.heartbeat_at = old

        await db.commit()

        recovered = await JobRecoveryService(
            db,
            lease_seconds=1,
        ).recover_abandoned(
            user_id=user_id,
        )

        recovered_job = next(item for item in recovered if item.id == job.id)

        assert recovered_job.status == "queued"

        events = list(
            (
                await db.execute(
                    select(PlatformEvent).where(
                        PlatformEvent.user_id == user_id,
                        PlatformEvent.event_type == "job.dead_lettered",
                    )
                )
            )
            .scalars()
            .all()
        )

        matching = [
            event
            for event in events
            if (event.payload or {}).get("job_id") == str(job.id)
        ]

        assert matching == []

        break


@pytest.mark.asyncio
async def test_scoped_recovery_emits_no_foreign_dead_letter_event():
    from sqlalchemy import select

    from app.models.models import PlatformEvent

    user_a = uuid4()
    user_b = uuid4()

    old = datetime.now(timezone.utc) - timedelta(hours=1)

    async for db in get_db():
        service = JobService(db)

        job_a = await service.enqueue(
            user_id=user_a,
            job_type=f"test.recovery.event.a.{uuid4()}",
            payload={"owner": "a"},
            max_attempts=1,
        )

        job_b = await service.enqueue(
            user_id=user_b,
            job_type=f"test.recovery.event.b.{uuid4()}",
            payload={"owner": "b"},
            max_attempts=1,
        )

        for job, worker in (
            (job_a, "event-owner-a"),
            (job_b, "event-owner-b"),
        ):
            claimed = await JobWorker(
                db,
                worker_id=worker,
                registry=JobHandlerRegistry(),
            ).repo.claim_next_due(
                worker_id=worker,
                job_id=job.id,
            )

            assert claimed is not None
            assert claimed.attempts == 1

            claimed.locked_at = old
            claimed.heartbeat_at = old

        await db.commit()

        recovered = await JobRecoveryService(
            db,
            lease_seconds=1,
        ).recover_abandoned(
            user_id=user_a,
        )

        assert {item.id for item in recovered} == {
            job_a.id,
        }

        events = list(
            (
                await db.execute(
                    select(PlatformEvent).where(
                        PlatformEvent.event_type == "job.dead_lettered",
                    )
                )
            )
            .scalars()
            .all()
        )

        a_matches = [
            event
            for event in events
            if (event.payload or {}).get("job_id") == str(job_a.id)
        ]

        b_matches = [
            event
            for event in events
            if (event.payload or {}).get("job_id") == str(job_b.id)
        ]

        assert len(a_matches) == 1
        assert a_matches[0].user_id == user_a

        assert b_matches == []

        await db.refresh(job_b)

        assert job_b.status == "running"
        assert job_b.locked_by == "event-owner-b"

        break
