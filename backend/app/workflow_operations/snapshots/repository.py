from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import WorkflowRunSnapshot


class WorkflowSnapshotRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
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
        seq_result = await self.db.execute(
            select(func.coalesce(func.max(WorkflowRunSnapshot.seq), 0)).where(
                WorkflowRunSnapshot.workflow_run_id == workflow_run_id
            )
        )
        seq = int(seq_result.scalar() or 0) + 1

        snapshot = WorkflowRunSnapshot(
            workflow_run_id=workflow_run_id,
            user_id=user_id,
            snapshot_type=snapshot_type,
            node_id=node_id,
            node_type=node_type,
            state=state or {},
            event=event or {},
            seq=seq,
        )

        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)
        return snapshot

    async def list_for_run(
        self,
        *,
        workflow_run_id: UUID,
        user_id: UUID | None = None,
        limit: int = 200,
    ):
        query = select(WorkflowRunSnapshot).where(
            WorkflowRunSnapshot.workflow_run_id == workflow_run_id
        )

        if user_id is not None:
            query = query.where(WorkflowRunSnapshot.user_id == user_id)

        result = await self.db.execute(
            query.order_by(WorkflowRunSnapshot.seq.asc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get(
        self,
        *,
        snapshot_id: UUID,
        user_id: UUID | None = None,
    ):
        query = select(WorkflowRunSnapshot).where(WorkflowRunSnapshot.id == snapshot_id)

        if user_id is not None:
            query = query.where(WorkflowRunSnapshot.user_id == user_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()
