from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.jobs.service import JobService
from app.workflow_operations.snapshots.service import WorkflowSnapshotService


class WorkflowReplayService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.snapshots = WorkflowSnapshotService(db)
        self.jobs = JobService(db)

    async def create_replay_job(
        self,
        *,
        user_id,
        snapshot_id: UUID,
    ):
        snapshot = await self.snapshots.get_or_404(
            snapshot_id=snapshot_id,
            user_id=user_id,
        )

        job = await self.jobs.enqueue(
            user_id=user_id,
            job_type="workflow.replay",
            payload={
                "snapshot_id": str(snapshot.id),
                "workflow_run_id": str(snapshot.workflow_run_id),
                "snapshot_seq": snapshot.seq,
                "snapshot_type": snapshot.snapshot_type,
            },
            max_attempts=1,
        )

        return {
            "snapshot": snapshot,
            "job": job,
        }
