from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import WorkflowSchedule


class WorkflowScheduleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        user_id,
        name: str,
        workflow_id,
        schedule_type: str,
        interval_seconds: int | None,
        cron_expression: str | None,
        next_run_at: datetime,
        timezone_name: str,
        max_runs: int | None,
        payload: dict,
    ):
        obj = WorkflowSchedule(
            user_id=user_id,
            name=name,
            workflow_id=workflow_id,
            schedule_type=schedule_type,
            interval_seconds=interval_seconds,
            cron_expression=cron_expression,
            next_run_at=next_run_at,
            timezone=timezone_name,
            max_runs=max_runs,
            payload=payload or {},
            status="active",
        )

        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get_for_user(self, *, user_id, schedule_id: UUID):
        result = await self.db.execute(
            select(WorkflowSchedule).where(
                WorkflowSchedule.user_id == user_id,
                WorkflowSchedule.id == schedule_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, *, user_id, limit: int = 100):
        result = await self.db.execute(
            select(WorkflowSchedule)
            .where(WorkflowSchedule.user_id == user_id)
            .order_by(WorkflowSchedule.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def due(self, *, user_id=None, limit: int = 50):
        now = datetime.now(timezone.utc)

        query = select(WorkflowSchedule).where(
            WorkflowSchedule.status == "active",
            WorkflowSchedule.next_run_at <= now,
        )

        if user_id is not None:
            query = query.where(
                WorkflowSchedule.user_id == user_id,
            )

        result = await self.db.execute(
            query.order_by(WorkflowSchedule.next_run_at.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        )

        return list(result.scalars().all())

    async def save(self, schedule: WorkflowSchedule):
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule
