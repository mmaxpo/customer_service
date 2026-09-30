from copy import deepcopy
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflow_operations.snapshots.repository import WorkflowSnapshotRepository
from app.workflow_operations.snapshots.json_safe import make_json_safe


class WorkflowSnapshotService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = WorkflowSnapshotRepository(db)

    async def capture(
        self,
        *,
        workflow_run_id,
        user_id,
        snapshot_type: str,
        state: dict,
        event: dict | None = None,
        node_id: str | None = None,
        node_type: str | None = None,
    ):
        return await self.repo.create(
            workflow_run_id=workflow_run_id,
            user_id=user_id,
            snapshot_type=snapshot_type,
            state=make_json_safe(deepcopy(state)),
            event=make_json_safe(deepcopy(event or {})),
            node_id=node_id,
            node_type=node_type,
        )

    async def list_for_run(
        self,
        *,
        workflow_run_id: UUID,
        user_id: UUID | None = None,
    ):
        return await self.repo.list_for_run(
            workflow_run_id=workflow_run_id,
            user_id=user_id,
        )

    async def get_or_404(
        self,
        *,
        snapshot_id: UUID,
        user_id: UUID | None = None,
    ):
        snapshot = await self.repo.get(
            snapshot_id=snapshot_id,
            user_id=user_id,
        )
        if snapshot is None:
            raise HTTPException(
                status_code=404,
                detail="Workflow snapshot not found",
            )
        return snapshot
