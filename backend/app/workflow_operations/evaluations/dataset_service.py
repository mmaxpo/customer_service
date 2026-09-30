from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.workflow_operations.evaluations.dataset_repository import (
    WorkflowEvalDatasetRepository,
)
from app.workflow_operations.evaluations.schemas import (
    WorkflowEvalDatasetCreate,
)
from app.models.models import (
    WorkflowEvalCase,
    WorkflowEvalDataset,
)


class WorkflowEvalDatasetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = WorkflowEvalDatasetRepository(db)

    async def create(
        self,
        *,
        user_id: UUID,
        payload: WorkflowEvalDatasetCreate,
    ) -> WorkflowEvalDataset:

        dataset = WorkflowEvalDataset(
            user_id=user_id,
            name=payload.name,
            description=payload.description,
            domain=payload.domain,
            metadata_json=payload.metadata_json,
        )

        dataset.cases = [
            WorkflowEvalCase(
                name=case.name,
                input_payload=case.input_payload,
                expected_output=case.expected_output,
                expected_status=case.expected_status,
                tags=case.tags,
                priority=case.priority,
                metadata_json=case.metadata_json,
            )
            for case in payload.cases
        ]

        return await self.repo.create(dataset)

    async def get(
        self,
        *,
        dataset_id: UUID,
    ):
        return await self.repo.get(
            dataset_id=dataset_id,
        )

    async def list_for_user(
        self,
        *,
        user_id: UUID,
    ):
        return await self.repo.list_for_user(
            user_id=user_id,
        )
