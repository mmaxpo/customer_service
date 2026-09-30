from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import (
    WorkflowEvalCase,
    WorkflowEvalDataset,
)


class WorkflowEvalDatasetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        dataset: WorkflowEvalDataset,
    ) -> WorkflowEvalDataset:
        self.db.add(dataset)
        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset

    async def get(
        self,
        *,
        dataset_id: UUID,
    ) -> WorkflowEvalDataset | None:
        result = await self.db.execute(
            select(WorkflowEvalDataset)
            .options(selectinload(WorkflowEvalDataset.cases))
            .where(WorkflowEvalDataset.id == dataset_id)
        )

        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        *,
        user_id: UUID,
    ) -> list[WorkflowEvalDataset]:
        result = await self.db.execute(
            select(WorkflowEvalDataset)
            .options(selectinload(WorkflowEvalDataset.cases))
            .where(WorkflowEvalDataset.user_id == user_id)
            .order_by(WorkflowEvalDataset.created_at.desc())
        )

        return list(result.scalars().unique().all())

    async def delete(
        self,
        *,
        dataset: WorkflowEvalDataset,
    ) -> None:
        await self.db.delete(dataset)
        await self.db.commit()
