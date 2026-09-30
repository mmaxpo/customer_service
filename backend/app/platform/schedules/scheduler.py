from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.jobs.service import JobService
from app.platform.schedules.repository import WorkflowScheduleRepository
from app.platform.schedules.service import compute_next_run


class WorkflowScheduler:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = WorkflowScheduleRepository(db)
        self.jobs = JobService(db)

    async def tick(self, *, user_id=None, limit: int = 50):
        enqueued = []

        for _ in range(limit):
            due = await self.repo.due(
                user_id=user_id,
                limit=1,
            )

            if not due:
                break

            schedule = due[0]
            job_payload = {
                **(schedule.payload or {}),
                "schedule_id": str(schedule.id),
            }

            if schedule.workflow_id is not None:
                job_payload.setdefault("workflow_id", str(schedule.workflow_id))

            job = await self.jobs.enqueue(
                user_id=schedule.user_id,
                job_type="workflow.run",
                payload=job_payload,
                max_attempts=3,
                commit=False,
            )

            now = datetime.now(timezone.utc)
            schedule.last_run_at = now
            schedule.run_count += 1

            next_run = compute_next_run(schedule, now=now)

            should_complete = False

            if next_run is None:
                should_complete = True

            if (
                schedule.max_runs is not None
                and schedule.run_count >= schedule.max_runs
            ):
                should_complete = True

            if should_complete:
                schedule.status = "completed"
            else:
                schedule.next_run_at = next_run

            await self.repo.save(schedule)

            enqueued.append(
                {
                    "schedule_id": str(schedule.id),
                    "job_id": str(job.id),
                    "job_type": job.job_type,
                    "schedule_status": schedule.status,
                    "run_count": schedule.run_count,
                }
            )

        return enqueued
