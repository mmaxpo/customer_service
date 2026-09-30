from __future__ import annotations

from uuid import UUID

from app.models.models import WorkflowDeployment
from app.workflow_operations.deployments.repository import WorkflowDeploymentRepository
from app.workflow_operations.deployments.schemas import (
    WorkflowDeploymentCreate,
    WorkflowDeploymentRollbackRequest,
)


class WorkflowDeploymentService:
    def __init__(self, db):
        self.db = db
        self.repo = WorkflowDeploymentRepository(db)

    async def deploy(
        self,
        payload: WorkflowDeploymentCreate,
    ):
        deployment = WorkflowDeployment(
            workflow_key=payload.workflow_key,
            workflow_version_id=payload.workflow_version_id,
            environment=payload.environment,
            deployed_by=payload.deployed_by,
            metadata_json=payload.metadata_json,
        )

        return await self.repo.create(deployment)

    async def rollback(
        self,
        *,
        workflow_key: str,
        environment: str,
        payload: WorkflowDeploymentRollbackRequest,
        deployed_by: UUID | None = None,
    ):
        current = await self.repo.latest(
            workflow_key=workflow_key,
            environment=environment,
        )

        rollback = WorkflowDeployment(
            workflow_key=workflow_key,
            workflow_version_id=payload.target_workflow_version_id,
            environment=environment,
            deployed_by=deployed_by,
            metadata_json={
                "rollback": True,
                "reason": payload.reason,
                "previous_workflow_version_id": (
                    str(current.workflow_version_id) if current else None
                ),
            },
        )

        saved = await self.repo.create(rollback)

        return {
            "rolled_back_from": (current.workflow_version_id if current else None),
            "rolled_back_to": saved.workflow_version_id,
            "reason": payload.reason,
        }

    async def latest(
        self,
        *,
        workflow_key: str,
        environment: str = "production",
    ):
        return await self.repo.latest(
            workflow_key=workflow_key,
            environment=environment,
        )

    async def list_for_workflow(
        self,
        *,
        workflow_key: str,
    ):
        return await self.repo.list_for_workflow(
            workflow_key=workflow_key,
        )
