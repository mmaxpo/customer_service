from datetime import datetime, timezone
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
async def test_cron_schedule_api_create():
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
                    "name": "Daily 9 AM",
                    "schedule_type": "cron",
                    "cron_expression": "0 9 * * *",
                    "next_run_at": datetime.now(timezone.utc).isoformat(),
                    "timezone": "Asia/Kolkata",
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
            assert data["schedule_type"] == "cron"
            assert data["cron_expression"] == "0 9 * * *"
            assert data["timezone"] == "Asia/Kolkata"

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_invalid_cron_expression_rejected():
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
                    "name": "Bad cron",
                    "schedule_type": "cron",
                    "cron_expression": "bad cron",
                    "next_run_at": datetime.now(timezone.utc).isoformat(),
                    "timezone": "UTC",
                    "payload": {},
                },
            )

            assert response.status_code == 422

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_cron_tick_reschedules_next_run():
    user_id = uuid4()

    async for db in get_db():
        schedule = await WorkflowScheduleService(db).create(
            user_id=user_id,
            payload=WorkflowScheduleCreate(
                name="Every minute",
                schedule_type="cron",
                cron_expression="* * * * *",
                next_run_at=datetime.now(timezone.utc),
                timezone="UTC",
                payload={
                    "workflow": {
                        "nodes": [],
                        "edges": [],
                    },
                    "message": "scheduled",
                },
            ),
        )

        schedule.next_run_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        await WorkflowScheduleService(db).repo.save(schedule)

        result = await WorkflowScheduler(db).tick()
        created = next(
            item for item in result if item["schedule_id"] == str(schedule.id)
        )

        assert created["job_type"] == "workflow.run"
        assert created["run_count"] == 1
        assert created["schedule_status"] == "active"

        refreshed = await WorkflowScheduleService(db).get_for_user(
            user_id=user_id,
            schedule_id=schedule.id,
        )

        assert refreshed.next_run_at > datetime.now(timezone.utc)

        break
