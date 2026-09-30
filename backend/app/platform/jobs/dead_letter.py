from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PlatformDeadLetter


class DeadLetterRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_from_job(
        self,
        *,
        job,
        error_message: str,
        commit: bool = True,
    ):
        dlq = PlatformDeadLetter(
            job_id=job.id,
            user_id=job.user_id,
            job_type=job.job_type,
            payload=job.payload or {},
            error_message=error_message,
            attempts=job.attempts,
            status="dead",
        )

        self.db.add(dlq)

        if commit:
            await self.db.commit()
            await self.db.refresh(dlq)
        else:
            await self.db.flush()

        return dlq

    async def list_for_user(self, *, user_id, limit: int = 100):
        result = await self.db.execute(
            select(PlatformDeadLetter)
            .where(PlatformDeadLetter.user_id == user_id)
            .order_by(PlatformDeadLetter.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get(self, dead_letter_id):
        result = await self.db.execute(
            select(PlatformDeadLetter).where(
                PlatformDeadLetter.id == dead_letter_id,
            )
        )
        return result.scalar_one_or_none()

    async def mark_replayed(self, dead_letter):
        dead_letter.status = "replayed"
        await self.db.commit()
        await self.db.refresh(dead_letter)
        return dead_letter
