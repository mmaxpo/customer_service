from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.security.rbac import (
    require_customer_service_permission,
)
from app.domains.customer_service.services.automation_studio import (
    AutomationStudioService,
)

studio_router = APIRouter(tags=["Customer Service - Automation Studio"])


class ProposalCreate(BaseModel):
    """Either a typed request or an edited graph (same patch path)."""

    workflow_id: UUID
    request: str | None = Field(default=None, min_length=3, max_length=2000)
    workflow: dict | None = None

    @model_validator(mode="after")
    def one_source(self):
        if (self.request is None) == (self.workflow is None):
            raise ValueError("send either request or workflow")
        return self


class ProposalRefine(BaseModel):
    request: str = Field(min_length=3, max_length=2000)


class RunFlagCreate(BaseModel):
    note: str = Field(min_length=1, max_length=2000)
    step_id: str | None = None
    message_id: str | None = None


@studio_router.get("/workflows")
async def studio_workflows(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    return await AutomationStudioService(db).overview(workspace_id=current_user.id)


@studio_router.get("/workflows/{workflow_id}")
async def studio_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    return await AutomationStudioService(db).workflow_detail(
        workspace_id=current_user.id, subscription_id=workflow_id
    )


@studio_router.get("/node-library")
async def node_library(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await AutomationStudioService(db).node_library(workspace_id=current_user.id)


@studio_router.post("/proposals")
async def create_proposal(
    payload: ProposalCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await AutomationStudioService(db).create_proposal(
        workspace_id=current_user.id,
        subscription_id=payload.workflow_id,
        request=payload.request,
        workflow=payload.workflow,
    )


@studio_router.get("/proposals/{proposal_id}")
async def get_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    return await AutomationStudioService(db).get_proposal(
        workspace_id=current_user.id, proposal_id=proposal_id
    )


@studio_router.post("/proposals/{proposal_id}/refine")
async def refine_proposal(
    proposal_id: UUID,
    payload: ProposalRefine,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await AutomationStudioService(db).refine_proposal(
        workspace_id=current_user.id, proposal_id=proposal_id, request=payload.request
    )


@studio_router.post("/proposals/{proposal_id}/publish")
async def publish_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await AutomationStudioService(db).publish_proposal(
        workspace_id=current_user.id, proposal_id=proposal_id
    )


@studio_router.delete("/proposals/{proposal_id}", status_code=204)
async def discard_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    await AutomationStudioService(db).discard_proposal(
        workspace_id=current_user.id, proposal_id=proposal_id
    )


@studio_router.get("/review")
async def review_queue(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    return await AutomationStudioService(db).review_queue(workspace_id=current_user.id)


@studio_router.get("/runs/{run_id}")
async def run_detail(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    return await AutomationStudioService(db).run_detail(
        workspace_id=current_user.id, run_id=run_id
    )


@studio_router.post("/runs/{run_id}/flags")
async def flag_run(
    run_id: UUID,
    payload: RunFlagCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await AutomationStudioService(db).flag_run(
        workspace_id=current_user.id,
        reviewer_id=current_user.actor_user_id,
        run_id=run_id,
        step_id=payload.step_id,
        message_id=payload.message_id,
        note=payload.note,
    )


@studio_router.post("/runs/{run_id}/dismiss", status_code=204)
async def dismiss_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    await AutomationStudioService(db).dismiss_run(
        workspace_id=current_user.id,
        reviewer_id=current_user.actor_user_id,
        run_id=run_id,
    )
