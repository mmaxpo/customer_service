from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.core.session import get_db
from app.main import app
from app.platform.schedules.scheduler import WorkflowScheduler
from app.platform.schedules.schemas import WorkflowScheduleCreate
from app.platform.schedules.service import WorkflowScheduleService


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_schedule_api_create_list_pause_resume():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/schedules",
                json={
                    "name": "Daily workflow",
                    "schedule_type": "interval",
                    "interval_seconds": 3600,
                    "next_run_at": (
                        datetime.now(timezone.utc) + timedelta(hours=1)
                    ).isoformat(),
                    "payload": {
                        "workflow": {
                            "nodes": [],
                            "edges": [],
                        },
                        "message": "scheduled",
                    },
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "active"

            listed = await client.get("/schedules")
            assert listed.status_code == 200
            assert any(item["id"] == data["id"] for item in listed.json())

            paused = await client.post(f"/schedules/{data['id']}/pause")
            assert paused.status_code == 200
            assert paused.json()["status"] == "paused"

            resumed = await client.post(f"/schedules/{data['id']}/resume")
            assert resumed.status_code == 200
            assert resumed.json()["status"] == "active"

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_scheduler_tick_enqueues_once_schedule_and_completes():
    user_id = uuid4()

    async for db in get_db():
        # Isolate this test from old due schedules left in the dev database.
        from sqlalchemy import text

        await db.execute(
            text(
                "UPDATE workflow_schedules SET status = 'disabled' WHERE status = 'active'"
            )
        )
        await db.commit()

        schedule = await WorkflowScheduleService(db).create(
            user_id=user_id,
            payload=WorkflowScheduleCreate(
                name="Run once",
                schedule_type="once",
                next_run_at=datetime.now(timezone.utc) - timedelta(seconds=1),
                payload={
                    "workflow": {
                        "nodes": [],
                        "edges": [],
                    },
                    "message": "scheduled",
                },
            ),
        )

        result = await WorkflowScheduler(db).tick()

        assert len(result) >= 1
        created = next(
            item for item in result if item["schedule_id"] == str(schedule.id)
        )

        assert created["job_type"] == "workflow.run"
        assert created["schedule_status"] == "completed"
        assert created["run_count"] == 1

        break


@pytest.mark.asyncio
async def test_scheduler_tick_reschedules_interval_until_max_runs():
    user_id = uuid4()

    async for db in get_db():
        schedule = await WorkflowScheduleService(db).create(
            user_id=user_id,
            payload=WorkflowScheduleCreate(
                name="Interval",
                schedule_type="interval",
                interval_seconds=3600,
                next_run_at=datetime.now(timezone.utc) - timedelta(seconds=1),
                max_runs=1,
                payload={
                    "workflow": {
                        "nodes": [],
                        "edges": [],
                    },
                    "message": "scheduled",
                },
            ),
        )

        result = await WorkflowScheduler(db).tick()
        created = next(
            item for item in result if item["schedule_id"] == str(schedule.id)
        )

        assert created["run_count"] == 1
        assert created["schedule_status"] == "completed"

        break


@pytest.mark.asyncio
async def test_schedule_tick_http_is_scoped_to_current_user():
    from datetime import timedelta

    from sqlalchemy import select

    from app.core.session import SessionLocal
    from app.models.models import PlatformJob, WorkflowSchedule

    owner = FakeUser()
    foreign = FakeUser()

    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        own_schedule = WorkflowSchedule(
            user_id=owner.id,
            name="Own due schedule",
            schedule_type="once",
            next_run_at=now - timedelta(seconds=1),
            timezone="UTC",
            status="active",
            payload={
                "workflow": {
                    "nodes": [],
                    "edges": [],
                },
                "message": "own-schedule",
            },
        )

        foreign_schedule = WorkflowSchedule(
            user_id=foreign.id,
            name="Foreign due schedule",
            schedule_type="once",
            next_run_at=now - timedelta(seconds=1),
            timezone="UTC",
            status="active",
            payload={
                "workflow": {
                    "nodes": [],
                    "edges": [],
                },
                "message": "foreign-schedule",
            },
        )

        db.add_all([own_schedule, foreign_schedule])
        await db.commit()
        await db.refresh(own_schedule)
        await db.refresh(foreign_schedule)

        own_schedule_id = own_schedule.id
        foreign_schedule_id = foreign_schedule.id

    app.dependency_overrides[get_current_user] = lambda: owner

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/schedules/tick")

        assert response.status_code == 200

        async with SessionLocal() as db:
            own = await db.get(
                WorkflowSchedule,
                own_schedule_id,
            )
            foreign_row = await db.get(
                WorkflowSchedule,
                foreign_schedule_id,
            )

            jobs = list(
                (
                    await db.execute(
                        select(PlatformJob).where(
                            PlatformJob.job_type == "workflow.run",
                        )
                    )
                )
                .scalars()
                .all()
            )

        own_jobs = [
            job
            for job in jobs
            if (job.payload or {}).get("schedule_id") == str(own_schedule_id)
        ]

        foreign_jobs = [
            job
            for job in jobs
            if (job.payload or {}).get("schedule_id") == str(foreign_schedule_id)
        ]

        assert own.status == "completed"
        assert own.run_count == 1
        assert len(own_jobs) == 1

        assert foreign_row.status == "active"
        assert foreign_row.run_count == 0
        assert foreign_jobs == []

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_background_schedule_tick_remains_global():
    from datetime import timedelta

    from app.core.session import SessionLocal
    from app.models.models import WorkflowSchedule

    user_a = uuid4()
    user_b = uuid4()

    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        schedule_a = WorkflowSchedule(
            user_id=user_a,
            name="Global A",
            schedule_type="once",
            next_run_at=now - timedelta(seconds=1),
            timezone="UTC",
            status="active",
            payload={
                "workflow": {
                    "nodes": [],
                    "edges": [],
                },
                "message": "global-a",
            },
        )

        schedule_b = WorkflowSchedule(
            user_id=user_b,
            name="Global B",
            schedule_type="once",
            next_run_at=now - timedelta(seconds=1),
            timezone="UTC",
            status="active",
            payload={
                "workflow": {
                    "nodes": [],
                    "edges": [],
                },
                "message": "global-b",
            },
        )

        db.add_all([schedule_a, schedule_b])
        await db.commit()

        schedule_a_id = schedule_a.id
        schedule_b_id = schedule_b.id

        result = await WorkflowScheduler(db).tick()

        processed_ids = {item["schedule_id"] for item in result}

        assert str(schedule_a_id) in processed_ids
        assert str(schedule_b_id) in processed_ids


@pytest.mark.asyncio
async def test_concurrent_scheduler_ticks_enqueue_due_schedule_once():
    import asyncio

    from sqlalchemy import select

    from app.core.session import SessionLocal
    from app.models.models import PlatformJob, WorkflowSchedule

    user_id = uuid4()
    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        schedule = WorkflowSchedule(
            user_id=user_id,
            name="Concurrent scheduler claim",
            schedule_type="once",
            next_run_at=now - timedelta(seconds=1),
            timezone="UTC",
            status="active",
            payload={
                "workflow": {
                    "nodes": [],
                    "edges": [],
                },
                "message": "concurrent-schedule",
            },
        )

        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)

        schedule_id = schedule.id

    async with SessionLocal() as db1, SessionLocal() as db2:
        scheduler1 = WorkflowScheduler(db1)
        scheduler2 = WorkflowScheduler(db2)

        first_enqueue_flushed = asyncio.Event()
        allow_worker1_to_continue = asyncio.Event()

        original_enqueue = scheduler1.jobs.enqueue

        async def controlled_enqueue(**kwargs):
            job = await original_enqueue(**kwargs)

            first_enqueue_flushed.set()

            await allow_worker1_to_continue.wait()

            return job

        scheduler1.jobs.enqueue = controlled_enqueue

        worker1 = asyncio.create_task(
            scheduler1.tick(
                user_id=user_id,
                limit=1,
            )
        )

        await asyncio.wait_for(
            first_enqueue_flushed.wait(),
            timeout=10,
        )

        # Worker 1 has flushed its job but has not yet committed the
        # schedule transaction. Its FOR UPDATE claim must therefore
        # still protect this occurrence from worker 2.
        worker2_result = await asyncio.wait_for(
            scheduler2.tick(
                user_id=user_id,
                limit=1,
            ),
            timeout=10,
        )

        assert worker2_result == []

        allow_worker1_to_continue.set()

        worker1_result = await asyncio.wait_for(
            worker1,
            timeout=10,
        )

        assert len(worker1_result) == 1
        assert worker1_result[0]["schedule_id"] == str(schedule_id)

    async with SessionLocal() as db:
        schedule = await db.get(
            WorkflowSchedule,
            schedule_id,
        )

        jobs = list(
            (
                await db.execute(
                    select(PlatformJob).where(
                        PlatformJob.user_id == user_id,
                        PlatformJob.job_type == "workflow.run",
                    )
                )
            )
            .scalars()
            .all()
        )

        matching_jobs = [
            job
            for job in jobs
            if (job.payload or {}).get("schedule_id") == str(schedule_id)
        ]

        assert schedule is not None
        assert schedule.status == "completed"
        assert schedule.run_count == 1
        assert len(matching_jobs) == 1


@pytest.mark.asyncio
async def test_schedule_create_rejects_foreign_workflow_id_and_allows_owner():
    from sqlalchemy import delete, select

    from app.core.session import SessionLocal
    from app.models.models import WorkflowSchedule
    from app.runtime.workflows import build_runtime_workflow_repository

    owner = FakeUser()
    foreign = FakeUser()

    workflow_id = None
    created_schedule_id = None

    workflow = {
        "name": "CORE-5.9 ownership validation",
        "nodes": [
            {
                "id": "trigger",
                "data": {
                    "nodeType": "trigger.message",
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "text": "CORE-5.9-OK",
                },
            },
        ],
        "edges": [
            {
                "source": "trigger",
                "target": "response",
            },
        ],
    }

    try:
        async with SessionLocal() as db:
            saved = await build_runtime_workflow_repository(db).create(
                user_id=owner.id,
                name="CORE-5.9 owner workflow",
                workflow=workflow,
            )
            workflow_id = saved["id"]

        request_payload = {
            "name": "CORE-5.9 workflow reference",
            "workflow_id": str(workflow_id),
            "schedule_type": "once",
            "next_run_at": (
                datetime.now(timezone.utc) + timedelta(hours=1)
            ).isoformat(),
            "timezone": "UTC",
            "payload": {
                "message": "CORE-5.9",
            },
        }

        # Foreign user must not be allowed to create a schedule referencing
        # another user's saved workflow. Missing and foreign references share
        # the same not-found contract.
        app.dependency_overrides[get_current_user] = lambda: foreign

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            rejected = await client.post(
                "/schedules",
                json=request_payload,
            )

        assert rejected.status_code == 404
        assert rejected.json() == {"detail": "Workflow not found"}

        async with SessionLocal() as db:
            foreign_rows = list(
                (
                    await db.execute(
                        select(WorkflowSchedule).where(
                            WorkflowSchedule.user_id == foreign.id,
                            WorkflowSchedule.workflow_id == workflow_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

        assert foreign_rows == []

        # The actual owner must still be able to create the same schedule.
        app.dependency_overrides[get_current_user] = lambda: owner

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            accepted = await client.post(
                "/schedules",
                json=request_payload,
            )

        assert accepted.status_code == 200, accepted.text

        created = accepted.json()
        created_schedule_id = created["id"]

        assert created["user_id"] == str(owner.id)
        assert created["workflow_id"] == str(workflow_id)
        assert created["status"] == "active"

    finally:
        app.dependency_overrides.pop(get_current_user, None)

        async with SessionLocal() as db:
            if created_schedule_id is not None:
                await db.execute(
                    delete(WorkflowSchedule).where(
                        WorkflowSchedule.id == created_schedule_id,
                    )
                )
                await db.commit()

            if workflow_id is not None:
                await build_runtime_workflow_repository(db).delete(
                    user_id=owner.id,
                    workflow_id=workflow_id,
                )


@pytest.mark.asyncio
async def test_concurrent_scheduler_ticks_do_not_duplicate_later_claimed_schedule():
    import asyncio

    from sqlalchemy import delete, select

    from app.core.session import SessionLocal
    from app.models.models import PlatformJob, WorkflowSchedule

    user_id = uuid4()
    now = datetime.now(timezone.utc)

    schedule_a_id = None
    schedule_b_id = None

    try:
        async with SessionLocal() as db:
            schedule_a = WorkflowSchedule(
                user_id=user_id,
                name="Concurrent batch A",
                schedule_type="once",
                next_run_at=now - timedelta(seconds=2),
                timezone="UTC",
                status="active",
                payload={
                    "workflow": {
                        "nodes": [],
                        "edges": [],
                    },
                    "message": "concurrent-batch-a",
                },
            )

            schedule_b = WorkflowSchedule(
                user_id=user_id,
                name="Concurrent batch B",
                schedule_type="once",
                next_run_at=now - timedelta(seconds=1),
                timezone="UTC",
                status="active",
                payload={
                    "workflow": {
                        "nodes": [],
                        "edges": [],
                    },
                    "message": "concurrent-batch-b",
                },
            )

            db.add_all([schedule_a, schedule_b])
            await db.commit()
            await db.refresh(schedule_a)
            await db.refresh(schedule_b)

            schedule_a_id = schedule_a.id
            schedule_b_id = schedule_b.id

        async with SessionLocal() as db1, SessionLocal() as db2:
            scheduler1 = WorkflowScheduler(db1)
            scheduler2 = WorkflowScheduler(db2)

            first_save_completed = asyncio.Event()
            allow_worker1_to_continue = asyncio.Event()

            original_save = scheduler1.repo.save
            save_count = 0

            async def controlled_save(schedule):
                nonlocal save_count

                result = await original_save(schedule)
                save_count += 1

                if save_count == 1:
                    first_save_completed.set()
                    await allow_worker1_to_continue.wait()

                return result

            scheduler1.repo.save = controlled_save

            worker1 = asyncio.create_task(
                scheduler1.tick(
                    user_id=user_id,
                    limit=2,
                )
            )

            await asyncio.wait_for(
                first_save_completed.wait(),
                timeout=10,
            )

            # Worker 1 has committed A but has NOT claimed B yet.
            # Worker 2 may safely claim and process B.
            worker2_result = await asyncio.wait_for(
                scheduler2.tick(
                    user_id=user_id,
                    limit=2,
                ),
                timeout=10,
            )

            allow_worker1_to_continue.set()

            worker1_result = await asyncio.wait_for(
                worker1,
                timeout=10,
            )

            processed_ids = {
                item["schedule_id"] for item in worker1_result + worker2_result
            }

            assert str(schedule_a_id) in processed_ids
            assert str(schedule_b_id) in processed_ids

        async with SessionLocal() as db:
            schedule_a = await db.get(
                WorkflowSchedule,
                schedule_a_id,
            )
            schedule_b = await db.get(
                WorkflowSchedule,
                schedule_b_id,
            )

            jobs = list(
                (
                    await db.execute(
                        select(PlatformJob).where(
                            PlatformJob.user_id == user_id,
                            PlatformJob.job_type == "workflow.run",
                        )
                    )
                )
                .scalars()
                .all()
            )

        jobs_a = [
            job
            for job in jobs
            if (job.payload or {}).get("schedule_id") == str(schedule_a_id)
        ]

        jobs_b = [
            job
            for job in jobs
            if (job.payload or {}).get("schedule_id") == str(schedule_b_id)
        ]

        assert schedule_a is not None
        assert schedule_b is not None

        assert schedule_a.status == "completed"
        assert schedule_b.status == "completed"

        assert schedule_a.run_count == 1
        assert schedule_b.run_count == 1

        assert len(jobs_a) == 1
        assert len(jobs_b) == 1

    finally:
        async with SessionLocal() as db:
            if schedule_a_id is not None or schedule_b_id is not None:
                ids = [
                    value
                    for value in (
                        schedule_a_id,
                        schedule_b_id,
                    )
                    if value is not None
                ]

                await db.execute(
                    delete(PlatformJob).where(
                        PlatformJob.user_id == user_id,
                        PlatformJob.job_type == "workflow.run",
                    )
                )

                await db.execute(
                    delete(WorkflowSchedule).where(WorkflowSchedule.id.in_(ids))
                )

                await db.commit()
