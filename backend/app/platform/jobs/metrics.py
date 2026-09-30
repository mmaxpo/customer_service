from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PlatformJob


class JobMetricsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def queue_depth(self, *, user_id=None) -> int:
        stmt = (
            select(func.count())
            .select_from(PlatformJob)
            .where(PlatformJob.status == "queued")
        )

        if user_id is not None:
            stmt = stmt.where(PlatformJob.user_id == user_id)

        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    async def counts_by_status(self, *, user_id=None) -> dict[str, int]:
        stmt = select(
            PlatformJob.status,
            func.count(),
        )

        if user_id is not None:
            stmt = stmt.where(PlatformJob.user_id == user_id)

        result = await self.db.execute(stmt.group_by(PlatformJob.status))

        return {row[0]: int(row[1]) for row in result.all()}

    async def counts_by_type(self, *, user_id=None) -> dict[str, int]:
        stmt = select(
            PlatformJob.job_type,
            func.count(),
        )

        if user_id is not None:
            stmt = stmt.where(PlatformJob.user_id == user_id)

        result = await self.db.execute(stmt.group_by(PlatformJob.job_type))

        return {row[0]: int(row[1]) for row in result.all()}
