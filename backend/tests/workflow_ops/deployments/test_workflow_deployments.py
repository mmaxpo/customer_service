from uuid import uuid4

import pytest

from app.core.session import get_db
from app.workflow_operations.deployments.schemas import (
    WorkflowDeploymentCreate,
    WorkflowDeploymentRollbackRequest,
)
from app.workflow_operations.deployments.service import WorkflowDeploymentService


@pytest.mark.asyncio
async def test_workflow_deployment_and_rollback():
    async for db in get_db():
        service = WorkflowDeploymentService(db)

        workflow_key = f"customer-support-{uuid4()}"

        version_1 = uuid4()
        version_2 = uuid4()

        deploy_1 = await service.deploy(
            WorkflowDeploymentCreate(
                workflow_key=workflow_key,
                workflow_version_id=version_1,
                environment="production",
                metadata_json={"stage": "first"},
            )
        )

        assert deploy_1.workflow_version_id == version_1
        assert deploy_1.metadata_json["stage"] == "first"

        deploy_2 = await service.deploy(
            WorkflowDeploymentCreate(
                workflow_key=workflow_key,
                workflow_version_id=version_2,
                environment="production",
                metadata_json={"stage": "second"},
            )
        )

        assert deploy_2.workflow_version_id == version_2
        assert deploy_2.metadata_json["stage"] == "second"

        latest = await service.latest(
            workflow_key=workflow_key,
            environment="production",
        )

        assert latest is not None
        assert latest.workflow_version_id == version_2

        rollback = await service.rollback(
            workflow_key=workflow_key,
            environment="production",
            payload=WorkflowDeploymentRollbackRequest(
                target_workflow_version_id=version_1,
                reason="bad regression",
            ),
        )

        assert rollback["rolled_back_to"] == version_1
        assert rollback["rolled_back_from"] == version_2

        latest_after = await service.latest(
            workflow_key=workflow_key,
            environment="production",
        )

        assert latest_after is not None
        assert latest_after.workflow_version_id == version_1
        assert latest_after.metadata_json["rollback"] is True
        assert latest_after.metadata_json["reason"] == "bad regression"

        deployments = await service.list_for_workflow(
            workflow_key=workflow_key,
        )

        assert len(deployments) == 3

        break
