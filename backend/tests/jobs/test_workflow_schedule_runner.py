import pytest


def test_runner_schedule_tick_configuration():
    from app.platform.jobs.runner import JobWorkerRunner

    runner = JobWorkerRunner(
        schedule_tick_interval_seconds=2.5,
        health_maintenance_enabled=False,
    )

    assert runner.schedule_tick_interval_seconds == 2.5


def test_runner_rejects_non_positive_schedule_tick_interval():
    from app.platform.jobs.runner import JobWorkerRunner

    with pytest.raises(
        ValueError,
        match="schedule tick interval must be > 0",
    ):
        JobWorkerRunner(
            schedule_tick_interval_seconds=0,
            health_maintenance_enabled=False,
        )


@pytest.mark.asyncio
async def test_runner_ticks_workflow_schedules_automatically(
    monkeypatch,
):
    import app.platform.jobs.runner as runner_module

    events = []
    runner = None

    class FakeDatabaseSession:
        async def rollback(self):
            events.append("rollback")

        async def commit(self):
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
            return [{"schedule_id": "scheduled"}]

    class FakeJobWorker:
        def __init__(self, db, *, worker_id):
            assert db is fake_db
            assert worker_id == "schedule-runner-worker"

        async def run_once(self):
            events.append("ordinary_job_processed")
            return None

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
        "JobWorker",
        FakeJobWorker,
    )
    monkeypatch.setattr(
        runner_module.asyncio,
        "sleep",
        fake_sleep,
    )

    runner = runner_module.JobWorkerRunner(
        worker_id="schedule-runner-worker",
        idle_sleep_seconds=0.01,
        busy_sleep_seconds=0.01,
        recovery_interval_seconds=30,
        schedule_tick_interval_seconds=1,
        health_maintenance_enabled=False,
    )

    await runner.run_forever()

    assert "recovery" in events
    assert "schedule_tick" in events
    assert "ordinary_job_processed" in events

    assert events.index("schedule_tick") < events.index("ordinary_job_processed")

    assert "rollback" not in events
    assert events.count("iteration_commit") == 1


@pytest.mark.asyncio
async def test_runner_processes_jobs_when_schedule_tick_fails(
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
            events.append("schedule_rollback")

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

    class FailingWorkflowScheduler:
        def __init__(self, db):
            assert db is fake_db

        async def tick(self):
            events.append("schedule_tick_attempt")
            raise RuntimeError("schedule dependency unavailable")

    class FakeJobWorker:
        def __init__(self, db, *, worker_id):
            assert db is fake_db
            assert worker_id == "schedule-isolation-worker"

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
        FailingWorkflowScheduler,
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
        worker_id="schedule-isolation-worker",
        idle_sleep_seconds=0.01,
        busy_sleep_seconds=0.01,
        recovery_interval_seconds=30,
        schedule_tick_interval_seconds=1,
        health_maintenance_enabled=False,
    )

    await runner.run_forever()

    assert "schedule_tick_attempt" in events
    assert "schedule_rollback" in events
    assert "ordinary_job_processed" in events

    assert events.index("schedule_rollback") < events.index("ordinary_job_processed")

    assert fake_db.rollback_calls == 1
    assert fake_db.commit_calls == 1
