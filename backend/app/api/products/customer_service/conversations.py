from __future__ import annotations

# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/conversations.py
# ============================================================
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.workflows import get_event_sink, get_run_store
from app.core.session import get_db
from app.domains.customer_service.services.collaboration import CollaborationService
from app.domains.customer_service.schemas.agent_assist import (
    AgentAssistSuggestionRead,
    AgentAssistSuggestionRevisionRead,
    AgentAssistSuggestionUpdate,
    ReplySuggestionResponse,
)
from app.domains.customer_service.schemas.conversation_detail import (
    ConversationDetail,
)
from app.domains.customer_service.schemas.conversations import (
    ConversationCreate,
    ConversationMessageCreate,
    ConversationMessageRead,
    InternalNoteCreate,
)
from app.domains.customer_service.schemas.triage import (
    TriageRequest,
    TriageResult,
)
from app.domains.customer_service.schemas.commercial import ReplySendRequest
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
    require_customer_service_permission,
)
from app.domains.customer_service.services.agent_assist import (
    CustomerServiceAgentAssistService,
)
from app.domains.customer_service.services.inbox import InboxService
from app.domains.customer_service.services.messaging import (
    CustomerServiceMessagingService,
)
from app.domains.customer_service.services.internal_notes import InternalNoteService
from app.domains.customer_service.services.triage import (
    AutoTriageService,
)

conversations_router = APIRouter(tags=["Customer Service - Conversations"])


@conversations_router.post("/")
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await InboxService(db).create_conversation(
        user_id=current_user.id,
        payload=payload,
    )


@conversations_router.get("/")
async def list_conversations(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    shopify_connection_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    return await InboxService(db).list_conversations(
        current_user.id,
        limit=limit,
        offset=offset,
        shopify_connection_id=shopify_connection_id,
    )


@conversations_router.get(
    "/{conversation_id}/agent-assist/suggestions",
    response_model=list[AgentAssistSuggestionRead],
)
async def list_conversation_agent_assist_suggestions(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceAgentAssistService(
        db=db,
        user_id=current_user.id,
    ).list_conversation_suggestions(conversation_id)


@conversations_router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_detail(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    conversation = await InboxService(db).get_conversation_detail(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@conversations_router.delete(
    "/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.delete")),
):
    deleted = await InboxService(db).delete_conversation(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


@conversations_router.post(
    "/{conversation_id}/triage",
    response_model=TriageResult,
)
async def triage_conversation(
    conversation_id: UUID,
    payload: TriageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await AutoTriageService(db).classify_and_apply(
        user_id=current_user.id,
        conversation_id=conversation_id,
        message=payload.message,
        actor_id=getattr(current_user, "actor_user_id", current_user.id),
    )


@conversations_router.post("/{conversation_id}/internal-notes")
async def add_internal_note(
    conversation_id: UUID,
    payload: InternalNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    actor_id = getattr(current_user, "actor_user_id", current_user.id)
    note = await InternalNoteService(db).add_note(
        user_id=current_user.id,
        actor_id=actor_id,
        conversation_id=conversation_id,
        payload=payload,
    )
    # "@Name" in a note tells that teammate.
    await CollaborationService(db).notify_mentions(
        workspace_id=current_user.id,
        actor_id=actor_id,
        conversation_id=conversation_id,
        body=payload.body,
    )
    return note


@conversations_router.get(
    "/{conversation_id}/messages",
    response_model=list[ConversationMessageRead],
)
async def list_conversation_messages(
    conversation_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.read")),
):
    messages = await InboxService(db).list_messages(
        user_id=current_user.id,
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
    )

    if messages is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return messages


@conversations_router.post("/{conversation_id}/messages")
async def add_message(
    conversation_id: UUID,
    payload: ConversationMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await InboxService(db).add_message_for_user(
        user_id=current_user.id,
        conversation_id=conversation_id,
        payload=payload,
    )


@conversations_router.post("/{conversation_id}/reply")
async def send_conversation_reply(
    conversation_id: UUID,
    payload: ReplySendRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    from app.domains.customer_service.services.commercial_operations import (
        CommercialOperationsService,
    )

    actor_id = getattr(current_user, "actor_user_id", current_user.id)
    await CommercialOperationsService(
        db,
        workspace_id=current_user.id,
        actor_id=actor_id,
    ).require_entitlement("agent_replies")
    return await CustomerServiceMessagingService(db).send_reply(
        workspace_id=current_user.id,
        actor_user_id=actor_id,
        conversation_id=conversation_id,
        payload=payload,
    )


@conversations_router.post(
    "/{conversation_id}/agent-assist/reply-suggestion",
    response_model=ReplySuggestionResponse,
)
async def reply_suggestion(
    conversation_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    run_store=Depends(get_run_store),
    event_sink=Depends(get_event_sink),
):
    result = await CustomerServiceAgentAssistService(
        db=db,
        request=request,
        user_id=current_user.id,
        run_store=run_store,
        event_sink=event_sink,
    ).suggest_reply(conversation_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return result


@conversations_router.patch(
    "/agent-assist/suggestions/{suggestion_id}",
    response_model=AgentAssistSuggestionRead,
)
async def edit_agent_assist_suggestion(
    suggestion_id: UUID,
    payload: AgentAssistSuggestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceAgentAssistService(
        db=db,
        user_id=current_user.id,
    ).edit_suggestion(suggestion_id, payload)


@conversations_router.post(
    "/agent-assist/suggestions/{suggestion_id}/approve",
    response_model=AgentAssistSuggestionRead,
)
async def approve_agent_assist_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceAgentAssistService(
        db=db,
        user_id=current_user.id,
    ).approve_suggestion(suggestion_id)


@conversations_router.post(
    "/agent-assist/suggestions/{suggestion_id}/reject",
    response_model=AgentAssistSuggestionRead,
)
async def reject_agent_assist_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceAgentAssistService(
        db=db,
        user_id=current_user.id,
    ).reject_suggestion(suggestion_id)


@conversations_router.post(
    "/agent-assist/suggestions/{suggestion_id}/send",
    response_model=AgentAssistSuggestionRead,
)
async def send_agent_assist_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceAgentAssistService(
        db=db,
        user_id=current_user.id,
    ).send_suggestion(suggestion_id)


@conversations_router.get(
    "/agent-assist/suggestions/{suggestion_id}/revisions",
    response_model=list[AgentAssistSuggestionRevisionRead],
)
async def list_agent_assist_suggestion_revisions(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceAgentAssistService(
        db=db,
        user_id=current_user.id,
    ).list_revisions(suggestion_id)


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/tags.py
# ============================================================


from fastapi import APIRouter, Depends

from app.core.session import get_db
from app.domains.customer_service.schemas.tags import (
    ConversationTagCreate,
    ConversationTagRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.services.tags import ConversationTagService

tags_router = APIRouter(
    prefix="/conversations/{conversation_id}/tags",
    tags=["Customer Service - Tags"],
)


@tags_router.post("/", response_model=ConversationTagRead)
async def add_conversation_tag(
    conversation_id: UUID,
    payload: ConversationTagCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ConversationTagService(db).add_tag(
        user_id=current_user.id,
        conversation_id=conversation_id,
        name=payload.name,
    )


@tags_router.get("/", response_model=list[ConversationTagRead])
async def list_conversation_tags(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ConversationTagService(db).list_tags(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )


@tags_router.delete("/{name}")
async def remove_conversation_tag(
    conversation_id: UUID,
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ConversationTagService(db).remove_tag(
        user_id=current_user.id,
        conversation_id=conversation_id,
        name=name,
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/timeline.py
# ============================================================


from fastapi import APIRouter, Depends, Query

from app.core.session import get_db
from app.domains.customer_service.schemas.timeline import (
    ConversationTimelineEventRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.services.timeline import (
    ConversationTimelineService,
)

timeline_router = APIRouter(tags=["Customer Service - Timeline"])


@timeline_router.get(
    "/conversations/{conversation_id}/timeline",
    response_model=list[ConversationTimelineEventRead],
)
async def get_conversation_timeline(
    conversation_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ConversationTimelineService(db).get_timeline(
        user_id=current_user.id,
        conversation_id=conversation_id,
        limit=limit,
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/conversation_context.py
# ============================================================


from fastapi import APIRouter, Depends

from app.core.session import get_db
from app.domains.customer_service.schemas.conversation_context import (
    ConversationContextRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.services.conversation_context import (
    ConversationContextService,
)

conversation_context_router = APIRouter(
    tags=["Customer Service - Conversation Context"]
)


@conversation_context_router.get(
    "/conversations/{conversation_id}/context",
    response_model=ConversationContextRead,
)
async def get_conversation_context(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ConversationContextService(db).get_context(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/workspace_recommendations.py
# ============================================================


from fastapi import APIRouter, Depends

from app.core.session import get_db
from app.domains.customer_service.schemas.workspace_recommendations import (
    WorkspaceRecommendationsRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.services.workspace_recommendations import (
    WorkspaceRecommendationsService,
)

workspace_recommendations_router = APIRouter(
    tags=["Customer Service - Workspace Recommendations"]
)


@workspace_recommendations_router.get(
    "/conversations/{conversation_id}/workspace-recommendations",
    response_model=WorkspaceRecommendationsRead,
)
async def get_workspace_recommendations(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkspaceRecommendationsService(db).get_recommendations(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )


__all__ = [
    "conversations_router",
    "tags_router",
    "timeline_router",
    "conversation_context_router",
    "workspace_recommendations_router",
]
