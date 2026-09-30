from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.workflow_operations.diff.service import WorkflowStateDiffService
from app.workflow_operations.snapshots.service import WorkflowSnapshotService


class WorkflowSnapshotCompareService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.snapshots = WorkflowSnapshotService(db)
        self.diff = WorkflowStateDiffService()

    async def compare_snapshots(
        self,
        *,
        before_snapshot_id: UUID,
        after_snapshot_id: UUID,
        user_id: UUID | None = None,
    ) -> dict:

        before = await self.snapshots.get_or_404(
            snapshot_id=before_snapshot_id,
            user_id=user_id,
        )

        after = await self.snapshots.get_or_404(
            snapshot_id=after_snapshot_id,
            user_id=user_id,
        )

        comparison = self.diff.compare_states(
            before=before.state,
            after=after.state,
        )

        return {
            "status": "ok",
            "before_snapshot_id": str(before.id),
            "after_snapshot_id": str(after.id),
            "workflow_run_id": str(before.workflow_run_id),
            "diff": comparison,
        }
