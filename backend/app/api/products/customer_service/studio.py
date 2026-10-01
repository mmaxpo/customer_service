from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.security.rbac import (
    require_customer_service_permission,
)
from app.domains.customer_service.services.assignment_rules import AssignmentRulesService
from app.domains.customer_service.services.automation_studio import (
    AutomationStudioService,
)
from app.domains.customer_service.services.conversation_translation import (
    ConversationTranslationService,
)
from app.domains.customer_service.services.desk_insights import DeskInsightsService
from app.domains.customer_service.services.live_monitor import LiveMonitorService
from app.domains.customer_service.services.unanswered_topics import (
    UnansweredTopicsService,
)

studio_router = APIRouter(tags=["Customer Service - Automation Studio"])


@studio_router.get("/desk/insights")
async def desk_insights(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    return await DeskInsightsService(db).insights(workspace_id=current_user.id, days=days)


@studio_router.post("/conversations/{conversation_id}/translate")
async def translate_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    return await ConversationTranslationService(db).translate(
        workspace_id=current_user.id, conversation_id=conversation_id
    )


class TopicDismiss(BaseModel):
    topic: str = Field(min_length=1, max_length=120)


@studio_router.get("/unanswered-topics")
async def unanswered_topics(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    return await UnansweredTopicsService(db).topics(workspace_id=current_user.id)


@studio_router.post("/unanswered-topics/dismiss")
async def dismiss_unanswered_topic(
    payload: TopicDismiss,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await UnansweredTopicsService(db).dismiss(
        workspace_id=current_user.id, topic=payload.topic
    )


@studio_router.get("/live/now")
async def live_now(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    return await LiveMonitorService(db).now(workspace_id=current_user.id)


@studio_router.get("/live/activity")
async def live_activity(
    days: int = Query(default=7, ge=1, le=90),
    outcome: Literal["answered", "handed_over", "failed", "running", "waiting_approval"] | None = None,
    workflow_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    return await LiveMonitorService(db).activity(
        workspace_id=current_user.id, days=days, outcome=outcome, workflow_id=workflow_id
    )


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


class WorkflowDraftRequest(BaseModel):
    request: str = Field(min_length=3, max_length=2000)


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    topic: str | None = None
    keywords: list[str] = Field(min_length=1, max_length=12)
    workflow: dict


class WorkflowEnabled(BaseModel):
    enabled: bool


@studio_router.post("/workflows/draft")
async def draft_workflow(
    payload: WorkflowDraftRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await AutomationStudioService(db).draft_workflow(request=payload.request)


@studio_router.post("/workflows")
async def create_workflow(
    payload: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await AutomationStudioService(db).create_workflow(
        workspace_id=current_user.id, **payload.model_dump()
    )


@studio_router.post("/workflows/{workflow_id}/enabled")
async def set_workflow_enabled(
    workflow_id: UUID,
    payload: WorkflowEnabled,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await AutomationStudioService(db).set_workflow_enabled(
        workspace_id=current_user.id, subscription_id=workflow_id, enabled=payload.enabled
    )


class WorkflowKeywords(BaseModel):
    keywords: list[str] = Field(min_length=1, max_length=12)


@studio_router.post("/workflows/{workflow_id}/keywords")
async def set_workflow_keywords(
    workflow_id: UUID,
    payload: WorkflowKeywords,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await AutomationStudioService(db).set_workflow_keywords(
        workspace_id=current_user.id, subscription_id=workflow_id, keywords=payload.keywords
    )


@studio_router.delete("/workflows/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    await AutomationStudioService(db).delete_workflow(
        workspace_id=current_user.id, subscription_id=workflow_id
    )


class TopicRule(BaseModel):
    topic: str = Field(min_length=1, max_length=100)
    assignee: str = Field(min_length=1, max_length=64)


class AssignmentRules(BaseModel):
    topics: list[TopicRule] = Field(default_factory=list, max_length=20)
    default: str | None = Field(default=None, max_length=64)


@studio_router.get("/assignment-rules")
async def assignment_rules(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    return await AssignmentRulesService(db).rules(workspace_id=current_user.id)


@studio_router.put("/assignment-rules")
async def save_assignment_rules(
    payload: AssignmentRules,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await AssignmentRulesService(db).save(
        workspace_id=current_user.id,
        topics=[rule.model_dump() for rule in payload.topics],
        default=payload.default,
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


@studio_router.post("/proposals/{proposal_id}/test")
async def test_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await AutomationStudioService(db).test_proposal(
        workspace_id=current_user.id, proposal_id=proposal_id
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


@studio_router.get("/workflows/{workflow_id}/versions")
async def version_history(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    return await AutomationStudioService(db).version_history(
        workspace_id=current_user.id, subscription_id=workflow_id
    )


@studio_router.post("/workflows/{workflow_id}/versions/{version}/restore")
async def restore_version(
    workflow_id: UUID,
    version: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await AutomationStudioService(db).restore_version(
        workspace_id=current_user.id, subscription_id=workflow_id, version=version
    )
