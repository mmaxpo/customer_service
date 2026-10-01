from __future__ import annotations

# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/workflows.py
# ============================================================
from fastapi import APIRouter
from uuid import UUID
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.session import get_db
from app.domains.customer_service.schemas.conversations import ConversationMessageRead
from app.domains.customer_service.schemas.macros import (
    MacroCreate,
    MacroRead,
    MacroUpdate,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.security.rbac import (
    require_customer_service_permission,
)
from app.workflow_operations.snapshots.schemas import WorkflowRunSnapshotRead
from app.workflow_operations.waits.schemas import WorkflowWaitRead
from app.domains.customer_service.services.macros import MacroService
from app.domains.customer_service.schemas.workflow_templates import (
    SeedWorkflowTemplatesRead,
    WorkflowTemplateCloneRequest,
    WorkflowTemplateCreate,
    WorkflowTemplateRead,
    WorkflowTemplateUpdate,
)
from app.domains.customer_service.services.workflow_templates import (
    WorkflowTemplateService,
)
from app.domains.customer_service.schemas.workflow_executions import (
    CustomerServiceWorkflowExecutionRead,
    CustomerServiceWorkflowTemplateRunRequest,
)
from app.domains.customer_service.services.workflow_executions import (
    CustomerServiceWorkflowExecutionService,
)
from fastapi import Response, status
from app.domains.customer_service.schemas.event_subscriptions import (
    EventSubscriptionCreate,
    EventSubscriptionRead,
    EventSubscriptionUpdate,
    SeedEventSubscriptionsRead,
)
from app.domains.customer_service.services.event_subscriptions import (
    CustomerServiceEventSubscriptionService,
)

workflows_router = APIRouter(tags=["Customer Service - Workflows"])


@workflows_router.get("/")
async def get_workflows():
    return {"workflows": []}


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/macros.py
# ============================================================




macros_router = APIRouter(prefix="/macros", tags=["Customer Service - Macros"])


@macros_router.post("/", response_model=MacroRead)
async def create_macro(
    payload: MacroCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.macros.manage")),
):
    return await MacroService(db).create(
        user_id=current_user.id,
        actor_id=getattr(current_user, "actor_user_id", current_user.id),
        payload=payload,
    )


@macros_router.get("/", response_model=list[MacroRead])
async def list_macros(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await MacroService(db).list(user_id=current_user.id, active_only=active_only)


@macros_router.patch("/{macro_id}", response_model=MacroRead)
async def update_macro(
    macro_id: UUID,
    payload: MacroUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.macros.manage")),
):
    return await MacroService(db).update(
        user_id=current_user.id,
        actor_id=getattr(current_user, "actor_user_id", current_user.id),
        macro_id=macro_id,
        payload=payload,
    )


@macros_router.post(
    "/{macro_id}/apply/{conversation_id}", response_model=ConversationMessageRead
)
async def apply_macro(
    macro_id: UUID,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.macros.manage")),
):
    return await MacroService(db).apply_to_conversation(
        user_id=current_user.id,
        actor_id=getattr(current_user, "actor_user_id", current_user.id),
        macro_id=macro_id,
        conversation_id=conversation_id,
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/workflow_templates.py
# ============================================================



workflow_templates_router = APIRouter(tags=["Customer Service Workflow Templates"])


@workflow_templates_router.post(
    "/workflow-templates", response_model=WorkflowTemplateRead
)
async def create_template(
    payload: WorkflowTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):

    return await WorkflowTemplateService(db).create(current_user.id, payload)


@workflow_templates_router.get(
    "/workflow-templates", response_model=list[WorkflowTemplateRead]
)
async def list_templates(
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):

    return await WorkflowTemplateService(db).list(current_user.id)


@workflow_templates_router.post(
    "/workflow-templates/seed-shopify", response_model=SeedWorkflowTemplatesRead
)
async def seed_shopify_templates(
    db: AsyncSession = Depends(get_db), current_user=Depends(require_customer_service_permission("cs.automation.manage"))
):

    return await WorkflowTemplateService(db).seed_shopify_system_templates()


@workflow_templates_router.post(
    "/workflow-templates/{template_id}/clone", response_model=WorkflowTemplateRead
)
async def clone_template(
    template_id,
    payload: WorkflowTemplateCloneRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):

    return await WorkflowTemplateService(db).clone(
        user_id=current_user.id, template_id=template_id, payload=payload
    )


@workflow_templates_router.patch(
    "/workflow-templates/{template_id}", response_model=WorkflowTemplateRead
)
async def update_template(
    template_id,
    payload: WorkflowTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):

    return await WorkflowTemplateService(db).update(
        user_id=current_user.id, template_id=template_id, payload=payload
    )


@workflow_templates_router.post(
    "/workflow-templates/{template_id}/publish", response_model=WorkflowTemplateRead
)
async def publish_template(
    template_id,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):

    return await WorkflowTemplateService(db).publish(
        user_id=current_user.id, template_id=template_id
    )


@workflow_templates_router.post(
    "/workflow-templates/{template_id}/unpublish", response_model=WorkflowTemplateRead
)
async def unpublish_template(
    template_id,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):

    return await WorkflowTemplateService(db).unpublish(
        user_id=current_user.id, template_id=template_id
    )


@workflow_templates_router.post(
    "/workflow-templates/seed-website-chat",
    response_model=SeedWorkflowTemplatesRead,
)
async def seed_website_chat_workflow_templates(
    db=Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await WorkflowTemplateService(db).seed_website_chat_system_templates()


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/workflow_executions.py
# ============================================================




workflow_executions_router = APIRouter(tags=["Customer Service Workflow Executions"])


@workflow_executions_router.get(
    "/workflow-executions",
    response_model=list[CustomerServiceWorkflowExecutionRead],
)
async def list_workflow_executions(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceWorkflowExecutionService(db).list(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@workflow_executions_router.get(
    "/workflow-executions/{job_id}",
    response_model=CustomerServiceWorkflowExecutionRead,
)
async def get_workflow_execution(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceWorkflowExecutionService(db).get(
        user_id=current_user.id,
        job_id=job_id,
    )


@workflow_executions_router.get(
    "/conversations/{conversation_id}/workflow-executions",
    response_model=list[CustomerServiceWorkflowExecutionRead],
)
async def list_conversation_workflow_executions(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceWorkflowExecutionService(db).list(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )


@workflow_executions_router.post(
    "/conversations/{conversation_id}/workflow-executions/run-template",
    response_model=CustomerServiceWorkflowExecutionRead,
)
async def run_workflow_template_for_conversation(
    conversation_id: UUID,
    payload: CustomerServiceWorkflowTemplateRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceWorkflowExecutionService(
        db
    ).run_template_for_conversation(
        user_id=current_user.id,
        conversation_id=conversation_id,
        template_id=payload.template_id,
        message=payload.message,
    )


@workflow_executions_router.get(
    "/tickets/{ticket_id}/workflow-executions",
    response_model=list[CustomerServiceWorkflowExecutionRead],
)
async def list_ticket_workflow_executions(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceWorkflowExecutionService(db).list(
        user_id=current_user.id,
        ticket_id=ticket_id,
    )


@workflow_executions_router.get(
    "/workflow-approvals", response_model=list[WorkflowWaitRead]
)
async def list_customer_service_workflow_approvals(
    status: str = "waiting",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(
        require_customer_service_permission("cs.automation.manage")
    ),
):
    return await CustomerServiceWorkflowExecutionService(db).list_approvals(
        user_id=current_user.id, status=status
    )


@workflow_executions_router.post("/workflow-approvals/{wait_id}/approve")
async def approve_customer_service_workflow(
    wait_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(
        require_customer_service_permission("cs.automation.manage")
    ),
):
    return await CustomerServiceWorkflowExecutionService(db).decide_approval(
        user_id=current_user.id, wait_id=wait_id, approved=True
    )


@workflow_executions_router.post("/workflow-approvals/{wait_id}/reject")
async def reject_customer_service_workflow(
    wait_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(
        require_customer_service_permission("cs.automation.manage")
    ),
):
    return await CustomerServiceWorkflowExecutionService(db).decide_approval(
        user_id=current_user.id, wait_id=wait_id, approved=False
    )


@workflow_executions_router.get("/workflow-executions/{job_id}/timeline")
async def get_customer_service_workflow_timeline(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceWorkflowExecutionService(db).timeline(
        user_id=current_user.id, job_id=job_id
    )


@workflow_executions_router.get(
    "/workflow-executions/{job_id}/snapshots",
    response_model=list[WorkflowRunSnapshotRead],
)
async def list_customer_service_workflow_snapshots(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceWorkflowExecutionService(db).snapshots(
        user_id=current_user.id, job_id=job_id
    )


@workflow_executions_router.post("/workflow-snapshots/{snapshot_id}/replay")
async def replay_customer_service_workflow_snapshot(
    snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(
        require_customer_service_permission("cs.automation.manage")
    ),
):
    return await CustomerServiceWorkflowExecutionService(db).replay_snapshot(
        user_id=current_user.id, snapshot_id=snapshot_id
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/event_subscriptions.py
# ============================================================




event_subscriptions_router = APIRouter(tags=["Customer Service Event Subscriptions"])


@event_subscriptions_router.post(
    "/event-subscriptions",
    response_model=EventSubscriptionRead,
)
async def create_event_subscription(
    payload: EventSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await CustomerServiceEventSubscriptionService(db).create(
        user_id=current_user.id,
        payload=payload,
    )


@event_subscriptions_router.get(
    "/event-subscriptions",
    response_model=list[EventSubscriptionRead],
)
async def list_event_subscriptions(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceEventSubscriptionService(db).list_for_user(
        user_id=current_user.id,
    )


@event_subscriptions_router.get(
    "/event-subscriptions/{subscription_id}",
    response_model=EventSubscriptionRead,
)
async def get_event_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceEventSubscriptionService(db).get(
        user_id=current_user.id,
        subscription_id=subscription_id,
    )


@event_subscriptions_router.patch(
    "/event-subscriptions/{subscription_id}",
    response_model=EventSubscriptionRead,
)
async def update_event_subscription(
    subscription_id: UUID,
    payload: EventSubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await CustomerServiceEventSubscriptionService(db).update(
        user_id=current_user.id,
        subscription_id=subscription_id,
        payload=payload,
    )


@event_subscriptions_router.delete(
    "/event-subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_event_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    await CustomerServiceEventSubscriptionService(db).delete(
        user_id=current_user.id,
        subscription_id=subscription_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@event_subscriptions_router.post(
    "/event-subscriptions/seed-shopify",
    response_model=SeedEventSubscriptionsRead,
)
async def seed_shopify_event_subscriptions(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await CustomerServiceEventSubscriptionService(
        db
    ).seed_shopify_template_subscriptions(
        user_id=current_user.id,
    )


@event_subscriptions_router.post(
    "/event-subscriptions/{subscription_id}/enable",
    response_model=EventSubscriptionRead,
)
async def enable_event_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await CustomerServiceEventSubscriptionService(db).set_active(
        user_id=current_user.id,
        subscription_id=subscription_id,
        is_active=True,
    )


@event_subscriptions_router.post(
    "/event-subscriptions/{subscription_id}/disable",
    response_model=EventSubscriptionRead,
)
async def disable_event_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.automation.manage")),
):
    return await CustomerServiceEventSubscriptionService(db).set_active(
        user_id=current_user.id,
        subscription_id=subscription_id,
        is_active=False,
    )


__all__ = [
    "workflows_router",
    "macros_router",
    "workflow_templates_router",
    "workflow_executions_router",
    "event_subscriptions_router",
]
