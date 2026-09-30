import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.models.models import PlatformJob
from app.runtime.capabilities.execution.health.maintenance import (
    CAPABILITY_HEALTH_RECONCILE_JOB_TYPE,
    CapabilityHealthMaintenanceTicker,
)


def test_health_maintenance_aligns_utc_bucket():
    bucket = CapabilityHealthMaintenanceTicker.align_bucket(
        now=datetime(
            2026,
            7,
            14,
            10,
            47,
            31,
            tzinfo=timezone.utc,
        ),
        window_hours=1,
    )

    assert bucket == datetime(
        2026,
        7,
        14,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )


def test_health_maintenance_aligns_multi_hour_bucket():
    bucket = CapabilityHealthMaintenanceTicker.align_bucket(
        now=datetime(
            2026,
            7,
            14,
            11,
            59,
            59,
            tzinfo=timezone.utc,
        ),
        window_hours=3,
    )

    assert bucket == datetime(
        2026,
        7,
        14,
        9,
        0,
        0,
        tzinfo=timezone.utc,
    )


@pytest.mark.asyncio
async def test_same_bucket_reuses_one_durable_job():
    now = datetime(
        2026,
        7,
        14,
        10,
        47,
        31,
        tzinfo=timezone.utc,
    )
    key_prefix = f"test-capability-health-maintenance:{uuid4()}"

    async with SessionLocal() as db:
        ticker = CapabilityHealthMaintenanceTicker(
            db,
            window_hours=1,
            lookback_windows=12,
            scope_limit=321,
            key_prefix=key_prefix,
        )

        first = await ticker.tick(now=now)
        second = await ticker.tick(now=now)

        jobs = list(
            (
                await db.execute(
                    select(PlatformJob).where(
                        PlatformJob.job_type == CAPABILITY_HEALTH_RECONCILE_JOB_TYPE,
                        PlatformJob.idempotency_key == first["idempotency_key"],
                    )
                )
            )
            .scalars()
            .all()
        )

    assert first["job_id"] == second["job_id"]
    assert len(jobs) == 1

    job = jobs[0]
    assert job.user_id is None
    assert job.payload["window_hours"] == 1
    assert job.payload["lookback_windows"] == 12
    assert job.payload["scope_limit"] == 321
    assert job.payload["maintenance_bucket"] == "2026-07-14T10:00:00+00:00"


@pytest.mark.asyncio
async def test_multiple_sessions_reuse_one_bucket_job():
    now = datetime(
        2026,
        7,
        14,
        12,
        15,
        tzinfo=timezone.utc,
    )
    key_prefix = f"test-capability-health-concurrent:{uuid4()}"

    async def tick_once():
        async with SessionLocal() as db:
            return await CapabilityHealthMaintenanceTicker(
                db,
                key_prefix=key_prefix,
            ).tick(now=now)

    first, second = await asyncio.gather(
        tick_once(),
        tick_once(),
    )

    assert first["idempotency_key"] == second["idempotency_key"]
    assert first["job_id"] == second["job_id"]


def test_runner_health_maintenance_configuration():
    from app.platform.jobs.runner import JobWorkerRunner

    runner = JobWorkerRunner(
        health_maintenance_enabled=True,
        health_maintenance_check_interval_seconds=15,
        health_window_hours=2,
        health_lookback_windows=48,
        health_scope_limit=500,
    )

    assert runner.health_maintenance_enabled is True
    assert runner.health_maintenance_check_interval_seconds == 15
    assert runner.health_window_hours == 2
    assert runner.health_lookback_windows == 48
    assert runner.health_scope_limit == 500


@pytest.mark.asyncio
async def test_runner_processes_job_when_health_maintenance_fails(
    monkeypatch,
):
    import app.platform.jobs.runner as runner_module

    events = []
    runner = None

    class FakeDatabaseSession:
        def __init__(self):
            self.rollback_calls = 0
            self.commit_calls = 0

        async def rollback(self):
            self.rollback_calls += 1
            events.append("maintenance_rollback")

        async def commit(self):
            self.commit_calls += 1
            events.append("iteration_commit")

    fake_db = FakeDatabaseSession()

    class FakeSessionContext:
        async def __aenter__(self):
            events.append("session_enter")
            return fake_db

        async def __aexit__(
            self,
            exc_type,
            exc,
            traceback,
        ):
            events.append("session_exit")
            return False

    def fake_session_local():
        return FakeSessionContext()

    class FakeRecoveryService:
        def __init__(self, db):
            assert db is fake_db

        async def recover_abandoned(self):
            events.append("recovery")
            return []

    class FakeWorkflowScheduler:
        def __init__(self, db):
            assert db is fake_db

        async def tick(self):
            events.append("schedule_tick")
            return []

    class FailingMaintenanceTicker:
        def __init__(self, db, **kwargs):
            assert db is fake_db

        async def tick(self):
            events.append("maintenance_attempt")
            raise RuntimeError("maintenance dependency unavailable")

    class FakeJobWorker:
        def __init__(self, db, *, worker_id):
            assert db is fake_db
            assert worker_id == "maintenance-isolation-worker"

        async def run_once(self):
            events.append("ordinary_job_processed")
            return object()

    async def fake_sleep(seconds):
        events.append("sleep")
        runner.stop()

    monkeypatch.setattr(
        runner_module,
        "SessionLocal",
        fake_session_local,
    )
    monkeypatch.setattr(
        runner_module,
        "JobRecoveryService",
        FakeRecoveryService,
    )
    monkeypatch.setattr(
        runner_module,
        "WorkflowScheduler",
        FakeWorkflowScheduler,
    )
    monkeypatch.setattr(
        runner_module,
        "CapabilityHealthMaintenanceTicker",
        FailingMaintenanceTicker,
    )
    monkeypatch.setattr(
        runner_module,
        "JobWorker",
        FakeJobWorker,
    )
    monkeypatch.setattr(
        runner_module.asyncio,
        "sleep",
        fake_sleep,
    )

    runner = runner_module.JobWorkerRunner(
        worker_id="maintenance-isolation-worker",
        idle_sleep_seconds=0.01,
        busy_sleep_seconds=0.01,
        recovery_interval_seconds=30,
        health_maintenance_enabled=True,
        health_maintenance_check_interval_seconds=1,
    )

    await runner.run_forever()

    assert "maintenance_attempt" in events
    assert "maintenance_rollback" in events
    assert "ordinary_job_processed" in events

    assert events.index("maintenance_rollback") < events.index("ordinary_job_processed")

    assert fake_db.rollback_calls == 1
    assert fake_db.commit_calls == 1
