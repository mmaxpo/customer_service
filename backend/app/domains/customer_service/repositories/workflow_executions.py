from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PlatformJob


class CustomerServiceWorkflowExecutionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID | None = None,
        ticket_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PlatformJob]:
        stmt = (
            select(PlatformJob)
            .where(
                PlatformJob.user_id == user_id,
                PlatformJob.job_type == "workflow.run",
            )
            .order_by(PlatformJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        jobs = list(result.scalars().all())

        if conversation_id is not None:
            jobs = [
                job
                for job in jobs
                if self._payload_event(job).get("conversation_id")
                == str(conversation_id)
            ]

        if ticket_id is not None:
            jobs = [
                job
                for job in jobs
                if self._payload_event(job).get("ticket_id") == str(ticket_id)
            ]

        return jobs

    async def get_for_user(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
    ) -> PlatformJob | None:
        result = await self.db.execute(
            select(PlatformJob).where(
                PlatformJob.user_id == user_id,
                PlatformJob.id == job_id,
                PlatformJob.job_type == "workflow.run",
            )
        )
        return result.scalar_one_or_none()

    def _payload_event(self, job: PlatformJob) -> dict:
        payload = job.payload or {}
        extras = payload.get("extras") or {}
        event = extras.get("event") or {}
        event_payload = event.get("payload") or {}
        return event_payload if isinstance(event_payload, dict) else {}
