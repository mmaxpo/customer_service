from sqlalchemy.ext.asyncio import AsyncSession

from app.workflow_operations.waits.repository import WorkflowWaitRepository
from app.workflow_operations.waits.service import WorkflowWaitService


class WorkflowWaitScheduler:
    def __init__(
        self,
        db: AsyncSession,
        *,
        worker_id: str = "workflow-wait-scheduler",
    ):
        self.db = db
        self.worker_id = worker_id
        self.repo = WorkflowWaitRepository(db)
        self.service = WorkflowWaitService(db)

    async def expire_due(self, *, user_id=None, limit: int = 100):
        """
        Backward-compatible method.

        Claims due time waits safely and enqueues workflow.resume jobs.

        When user_id is omitted this remains the global background scheduler
        behavior. HTTP callers pass user_id to enforce tenant isolation.
        """
        return await self.wake_due_time_waits(
            user_id=user_id,
            limit=limit,
        )

    async def wake_due_time_waits(self, *, user_id=None, limit: int = 100):
        waits = await self.repo.claim_due_time_waits(
            worker_id=self.worker_id,
            user_id=user_id,
            limit=limit,
        )

        expired = []

        for wait in waits:
            saved = await self.service.expire(wait=wait)
            expired.append(saved)

        return expired
