from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import WorkflowWait


class WorkflowWaitRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        user_id,
        workflow_run_id: str,
        node_id: str | None,
        wait_type: str,
        payload: dict,
        expires_at=None,
    ):
        wait = WorkflowWait(
            user_id=user_id,
            workflow_run_id=workflow_run_id,
            node_id=node_id,
            wait_type=wait_type,
            payload=payload or {},
            expires_at=expires_at,
            status="waiting",
        )

        self.db.add(wait)
        await self.db.commit()
        await self.db.refresh(wait)
        return wait

    async def get_for_user(self, *, user_id, wait_id: UUID):
        result = await self.db.execute(
            select(WorkflowWait).where(
                WorkflowWait.user_id == user_id,
                WorkflowWait.id == wait_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        *,
        user_id,
        status: str | None = None,
        workflow_run_id: str | None = None,
        limit: int = 100,
    ):
        stmt = (
            select(WorkflowWait)
            .where(WorkflowWait.user_id == user_id)
            .order_by(WorkflowWait.created_at.desc())
            .limit(limit)
        )

        if status:
            stmt = stmt.where(WorkflowWait.status == status)

        if workflow_run_id:
            stmt = stmt.where(WorkflowWait.workflow_run_id == workflow_run_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def due_expired(self, *, limit: int = 100):
        now = datetime.now(timezone.utc)

        result = await self.db.execute(
            select(WorkflowWait)
            .where(
                WorkflowWait.status == "waiting",
                WorkflowWait.expires_at.is_not(None),
                WorkflowWait.expires_at <= now,
            )
            .order_by(WorkflowWait.expires_at.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        )

        return list(result.scalars().all())

    async def claim_due_time_waits(
        self,
        *,
        worker_id: str,
        user_id=None,
        limit: int = 100,
    ):
        now = datetime.now(timezone.utc)

        stmt = select(WorkflowWait).where(
            WorkflowWait.status == "waiting",
            WorkflowWait.wait_type == "time",
            WorkflowWait.expires_at.is_not(None),
            WorkflowWait.expires_at <= now,
        )

        if user_id is not None:
            stmt = stmt.where(WorkflowWait.user_id == user_id)

        result = await self.db.execute(
            stmt.order_by(WorkflowWait.expires_at.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        )

        waits = list(result.scalars().all())

        for wait in waits:
            wait.status = "processing"
            wait.claimed_by = worker_id
            wait.claimed_at = now

        await self.db.commit()

        for wait in waits:
            await self.db.refresh(wait)

        return waits

    async def list_waiting_for_run(
        self,
        *,
        user_id,
        workflow_run_id: str,
    ):
        result = await self.db.execute(
            select(WorkflowWait)
            .where(
                WorkflowWait.user_id == user_id,
                WorkflowWait.workflow_run_id == str(workflow_run_id),
                WorkflowWait.status == "waiting",
            )
            .order_by(WorkflowWait.created_at.asc())
        )

        return list(result.scalars().all())

    async def resolve_waiting(
        self,
        *,
        user_id,
        wait_id: UUID,
        resolution: dict,
    ):
        """
        Atomically resolve a wait only when it is still waiting.

        This protects production from duplicate resume jobs caused by:
          - duplicate platform events
          - webhook retries
          - user double-clicking approval
          - two workers trying to resolve the same wait

        Returns None when the wait is missing or already resolved/expired/cancelled.
        """
        now = datetime.now(timezone.utc)

        result = await self.db.execute(
            select(WorkflowWait)
            .where(
                WorkflowWait.user_id == user_id,
                WorkflowWait.id == wait_id,
                WorkflowWait.status == "waiting",
            )
            .with_for_update(skip_locked=True)
        )

        wait = result.scalar_one_or_none()

        if wait is None:
            await self.db.rollback()
            return None

        wait.status = "resolved"
        wait.resolution = resolution or {}
        wait.resolved_at = now

        await self.db.commit()
        await self.db.refresh(wait)

        return wait

    async def save(self, wait: WorkflowWait):
        await self.db.commit()
        await self.db.refresh(wait)
        return wait
