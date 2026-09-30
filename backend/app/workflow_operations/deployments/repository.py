from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import WorkflowDeployment


class WorkflowDeploymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, deployment: WorkflowDeployment):
        self.db.add(deployment)
        await self.db.commit()
        await self.db.refresh(deployment)
        return deployment

    async def latest(
        self,
        *,
        workflow_key: str,
        environment: str,
    ):
        q = (
            select(WorkflowDeployment)
            .where(
                WorkflowDeployment.workflow_key == workflow_key,
                WorkflowDeployment.environment == environment,
            )
            .order_by(desc(WorkflowDeployment.created_at))
            .limit(1)
        )

        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list_for_workflow(
        self,
        *,
        workflow_key: str,
    ):
        q = (
            select(WorkflowDeployment)
            .where(
                WorkflowDeployment.workflow_key == workflow_key,
            )
            .order_by(desc(WorkflowDeployment.created_at))
        )

        result = await self.db.execute(q)
        return list(result.scalars().all())
