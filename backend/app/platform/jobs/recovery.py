from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PlatformJob
from app.platform.events.publisher import PlatformEventPublisher
from app.platform.jobs.dead_letter import DeadLetterRepository


class JobRecoveryService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        lease_seconds: int = 300,
    ):
        self.db = db
        self.lease_seconds = lease_seconds

    async def recover_abandoned(
        self,
        *,
        limit: int = 100,
        user_id=None,
    ) -> list[PlatformJob]:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.lease_seconds)

        stmt = select(PlatformJob).where(
            PlatformJob.status == "running",
            PlatformJob.locked_at.is_not(None),
            PlatformJob.locked_at <= cutoff,
        )

        if user_id is not None:
            stmt = stmt.where(PlatformJob.user_id == user_id)

        result = await self.db.execute(
            stmt.order_by(PlatformJob.locked_at.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        )

        jobs = list(result.scalars().all())
        terminal_jobs: list[PlatformJob] = []
        recovery_error = "Recovered abandoned running job"

        for job in jobs:
            if job.attempts >= job.max_attempts:
                job.status = "dead_letter"
                job.finished_at = datetime.now(timezone.utc)
                terminal_jobs.append(job)
            else:
                job.status = "queued"
                job.run_after = datetime.now(timezone.utc)

            job.locked_at = None
            job.locked_by = None
            job.error_message = recovery_error

        dead_letters = DeadLetterRepository(self.db)
        terminal_dead_letters = []

        for job in terminal_jobs:
            dead = await dead_letters.create_from_job(
                job=job,
                error_message=recovery_error,
                commit=False,
            )
            terminal_dead_letters.append((job, dead))

        # Persist recovery state and its DLQ records atomically
        # before dispatching lifecycle events. Event handlers may
        # commit their own durable projections, so they must not
        # execute inside the recovery transaction.
        await self.db.commit()

        for job in jobs:
            await self.db.refresh(job)

        for job, dead in terminal_dead_letters:
            await PlatformEventPublisher(self.db).publish(
                user_id=job.user_id,
                event_type="job.dead_lettered",
                source="jobs",
                payload={
                    "job_id": str(job.id),
                    "dead_letter_id": str(dead.id),
                    "job_type": job.job_type,
                    "attempts": job.attempts,
                    "error_message": recovery_error,
                },
                dispatch=True,
            )

        return jobs
