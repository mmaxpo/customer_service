from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.jobs.repository import JobRepository


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = JobRepository(db)

    async def enqueue(
        self,
        *,
        job_type: str,
        payload: dict,
        user_id=None,
        max_attempts: int = 3,
        run_after: datetime | None = None,
        idempotency_key: str | None = None,
        commit: bool = True,
    ):
        if not job_type or not job_type.strip():
            raise HTTPException(status_code=422, detail="job_type is required")

        if max_attempts < 1:
            raise HTTPException(status_code=422, detail="max_attempts must be >= 1")

        return await self.repo.enqueue(
            job_type=job_type,
            payload=payload,
            user_id=user_id,
            max_attempts=max_attempts,
            run_after=run_after,
            idempotency_key=idempotency_key,
            commit=commit,
        )

    async def get(
        self,
        *,
        job_id: UUID,
        user_id,
    ):
        job = await self.repo.get_for_user(
            job_id=job_id,
            user_id=user_id,
        )

        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")

        return job

    async def list_for_user(self, *, user_id, limit: int = 50):
        return await self.repo.list_for_user(
            user_id=user_id,
            limit=limit,
        )
