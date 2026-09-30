from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.jobs.dead_letter import DeadLetterRepository
from app.platform.jobs.service import JobService


class JobReplayService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.dead_letters = DeadLetterRepository(db)
        self.jobs = JobService(db)

    async def replay_dead_letter(self, *, user_id, dead_letter_id):
        dead = await self.dead_letters.get(dead_letter_id)

        if dead is None or dead.user_id != user_id:
            raise HTTPException(status_code=404, detail="Dead letter not found")

        if dead.status == "replayed":
            raise HTTPException(status_code=409, detail="Dead letter already replayed")

        job = await self.jobs.enqueue(
            user_id=dead.user_id,
            job_type=dead.job_type,
            payload={
                **(dead.payload or {}),
                "replayed_from_dead_letter_id": str(dead.id),
                "original_job_id": str(dead.job_id),
            },
            max_attempts=3,
        )

        await self.dead_letters.mark_replayed(dead)

        return job
