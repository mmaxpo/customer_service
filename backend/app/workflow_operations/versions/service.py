from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.workflow_operations.versions.repository import WorkflowVersionRepository
from app.workflow_operations.versions.schemas import (
    WorkflowDefinitionCreate,
    WorkflowVersionCreate,
)


class WorkflowVersionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = WorkflowVersionRepository(db)

    async def create_definition(
        self,
        *,
        user_id: UUID,
        payload: WorkflowDefinitionCreate,
    ) -> dict:
        return await self.repo.create_definition(
            user_id=user_id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            metadata_json=payload.metadata_json,
        )

    async def create_version(
        self,
        *,
        definition_id: UUID,
        user_id: UUID,
        payload: WorkflowVersionCreate,
    ) -> dict:
        definition = await self.repo.get_definition(
            definition_id=definition_id,
        )
        if not definition:
            raise ValueError("workflow_definition_not_found")

        if definition["user_id"] != user_id:
            raise PermissionError("workflow_definition_forbidden")

        return await self.repo.create_version(
            definition_id=definition_id,
            user_id=user_id,
            workflow_json=payload.workflow_json,
            notes=payload.notes,
            evaluation_summary=payload.evaluation_summary,
            metadata_json=payload.metadata_json,
        )

    async def list_versions(
        self,
        *,
        definition_id: UUID,
        user_id: UUID,
    ) -> list[dict]:
        definition = await self.repo.get_definition(
            definition_id=definition_id,
        )
        if not definition:
            raise ValueError("workflow_definition_not_found")

        if definition["user_id"] != user_id:
            raise PermissionError("workflow_definition_forbidden")

        return await self.repo.list_versions(
            definition_id=definition_id,
        )

    async def publish_version(
        self,
        *,
        definition_id: UUID,
        user_id: UUID,
        version: int,
    ) -> dict:
        definition = await self.repo.get_definition(
            definition_id=definition_id,
        )
        if not definition:
            raise ValueError("workflow_definition_not_found")

        if definition["user_id"] != user_id:
            raise PermissionError("workflow_definition_forbidden")

        return await self.repo.publish_version(
            definition_id=definition_id,
            version=version,
        )

    async def rollback(
        self,
        *,
        definition_id: UUID,
        user_id: UUID,
        version: int,
    ) -> dict:
        return await self.publish_version(
            definition_id=definition_id,
            user_id=user_id,
            version=version,
        )

    async def get_active_version(
        self,
        *,
        definition_id: UUID,
        user_id: UUID,
    ) -> dict | None:
        definition = await self.repo.get_definition(
            definition_id=definition_id,
        )
        if not definition:
            return None

        if definition["user_id"] != user_id:
            raise PermissionError("workflow_definition_forbidden")

        return await self.repo.get_active_version(
            definition_id=definition_id,
        )
