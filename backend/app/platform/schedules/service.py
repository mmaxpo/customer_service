from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.schedules.repository import WorkflowScheduleRepository
from app.runtime.workflows import build_runtime_workflow_repository


class WorkflowScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = WorkflowScheduleRepository(db)

    async def create(self, *, user_id, payload):
        self._validate_create(payload)

        if payload.workflow_id is not None:
            workflow = await build_runtime_workflow_repository(self.db).get(
                user_id=user_id,
                workflow_id=payload.workflow_id,
            )
            if workflow is None:
                raise HTTPException(status_code=404, detail="Workflow not found")

        next_run_at = self._compute_initial_next_run(payload)

        return await self.repo.create(
            user_id=user_id,
            name=payload.name,
            workflow_id=payload.workflow_id,
            schedule_type=payload.schedule_type,
            interval_seconds=payload.interval_seconds,
            cron_expression=payload.cron_expression,
            next_run_at=next_run_at,
            timezone_name=payload.timezone,
            max_runs=payload.max_runs,
            payload=payload.payload,
        )

    async def list_for_user(self, *, user_id):
        return await self.repo.list_for_user(user_id=user_id)

    async def get_for_user(self, *, user_id, schedule_id):
        schedule = await self.repo.get_for_user(
            user_id=user_id,
            schedule_id=schedule_id,
        )

        if schedule is None:
            raise HTTPException(status_code=404, detail="Schedule not found")

        return schedule

    async def pause(self, *, user_id, schedule_id):
        schedule = await self.get_for_user(
            user_id=user_id,
            schedule_id=schedule_id,
        )

        schedule.status = "paused"
        return await self.repo.save(schedule)

    async def resume(self, *, user_id, schedule_id):
        schedule = await self.get_for_user(
            user_id=user_id,
            schedule_id=schedule_id,
        )

        if schedule.status == "completed":
            raise HTTPException(
                status_code=409, detail="Cannot resume completed schedule"
            )

        schedule.status = "active"
        return await self.repo.save(schedule)

    def _validate_create(self, payload) -> None:
        self._get_timezone(payload.timezone)

        if payload.schedule_type == "interval":
            if not payload.interval_seconds or payload.interval_seconds < 60:
                raise HTTPException(
                    status_code=422,
                    detail="interval_seconds must be >= 60 for interval schedules",
                )

            if payload.cron_expression is not None:
                raise HTTPException(
                    status_code=422,
                    detail="cron_expression must be omitted for interval schedules",
                )

        if payload.schedule_type == "once":
            if payload.interval_seconds is not None:
                raise HTTPException(
                    status_code=422,
                    detail="interval_seconds must be omitted for once schedules",
                )

            if payload.cron_expression is not None:
                raise HTTPException(
                    status_code=422,
                    detail="cron_expression must be omitted for once schedules",
                )

        if payload.schedule_type == "cron":
            if not payload.cron_expression:
                raise HTTPException(
                    status_code=422,
                    detail="cron_expression is required for cron schedules",
                )

            if not croniter.is_valid(payload.cron_expression):
                raise HTTPException(
                    status_code=422,
                    detail="Invalid cron_expression",
                )

            if payload.interval_seconds is not None:
                raise HTTPException(
                    status_code=422,
                    detail="interval_seconds must be omitted for cron schedules",
                )

        if payload.max_runs is not None and payload.max_runs < 1:
            raise HTTPException(status_code=422, detail="max_runs must be >= 1")

    def _compute_initial_next_run(self, payload) -> datetime:
        if payload.schedule_type == "cron":
            tz = self._get_timezone(payload.timezone)
            base = datetime.now(tz)
            return (
                croniter(payload.cron_expression, base)
                .get_next(datetime)
                .astimezone(timezone.utc)
            )

        return self._ensure_aware(payload.next_run_at)

    def _ensure_aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    def _get_timezone(self, timezone_name: str):
        try:
            return ZoneInfo(timezone_name or "UTC")
        except ZoneInfoNotFoundError:
            raise HTTPException(status_code=422, detail="Invalid timezone") from None


def compute_next_run(schedule, *, now: datetime | None = None):
    now = now or datetime.now(timezone.utc)

    if schedule.schedule_type == "once":
        return None

    if schedule.schedule_type == "interval":
        if not schedule.interval_seconds:
            return None

        return now + timedelta(seconds=schedule.interval_seconds)

    if schedule.schedule_type == "cron":
        if not schedule.cron_expression:
            return None

        tz = ZoneInfo(schedule.timezone or "UTC")
        base = now.astimezone(tz)

        return (
            croniter(schedule.cron_expression, base)
            .get_next(datetime)
            .astimezone(timezone.utc)
        )

    return None
