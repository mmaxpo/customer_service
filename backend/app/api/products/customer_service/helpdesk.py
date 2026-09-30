from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.schemas.helpdesk import (
    BulkConversationActionRequest,
    ConversationModerationRequest,
    ConversationSnoozeRequest,
    CustomerCustomFieldsUpdate,
    ReplyDraftRead,
    ReplyDraftScheduleRequest,
    ReplyDraftWrite,
    ReplySignatureRead,
    ReplySignatureWrite,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal,
    require_customer_service_permission,
)
from app.domains.customer_service.services.helpdesk import (
    CustomerServiceHelpdeskService,
)


helpdesk_router = APIRouter(tags=["Customer Service - Helpdesk Operations"])


def _service(db, principal):
    return CustomerServiceHelpdeskService(
        db, workspace_id=principal.id, actor_user_id=principal.actor_user_id
    )


@helpdesk_router.post("/conversations/{conversation_id}/snooze")
async def snooze_conversation(
    conversation_id: UUID,
    payload: ConversationSnoozeRequest,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    return await _service(db, principal).snooze(conversation_id, payload)


@helpdesk_router.delete("/conversations/{conversation_id}/snooze")
async def wake_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    return await _service(db, principal).wake(conversation_id)


@helpdesk_router.post("/conversations/{conversation_id}/moderation")
async def moderate_conversation(
    conversation_id: UUID,
    payload: ConversationModerationRequest,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    return await _service(db, principal).moderate(conversation_id, payload)


@helpdesk_router.post("/conversations/bulk")
async def bulk_conversation_action(
    payload: BulkConversationActionRequest,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    return await _service(db, principal).bulk(payload)


@helpdesk_router.post(
    "/conversations/{conversation_id}/drafts",
    response_model=ReplyDraftRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_reply_draft(
    conversation_id: UUID,
    payload: ReplyDraftWrite,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    return await _service(db, principal).create_draft(conversation_id, payload)


@helpdesk_router.get(
    "/conversations/{conversation_id}/drafts", response_model=list[ReplyDraftRead]
)
async def list_reply_drafts(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal=Depends(get_customer_service_principal),
):
    return await _service(db, principal).list_drafts(conversation_id)


@helpdesk_router.put("/drafts/{draft_id}", response_model=ReplyDraftRead)
async def update_reply_draft(
    draft_id: UUID,
    payload: ReplyDraftWrite,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    return await _service(db, principal).update_draft(draft_id, payload)


@helpdesk_router.delete("/drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def discard_reply_draft(
    draft_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    await _service(db, principal).discard_draft(draft_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@helpdesk_router.post(
    "/drafts/{draft_id}/schedule",
    response_model=ReplyDraftRead,
)
async def schedule_reply_draft(
    draft_id: UUID,
    payload: ReplyDraftScheduleRequest,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    return await _service(
        db,
        principal,
    ).schedule_draft(
        draft_id,
        scheduled_for=payload.scheduled_for,
        expected_version=payload.expected_version,
    )


@helpdesk_router.delete(
    "/drafts/{draft_id}/schedule",
    response_model=ReplyDraftRead,
)
async def cancel_scheduled_reply_draft(
    draft_id: UUID,
    expected_version: int = Query(ge=1),
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    return await _service(
        db,
        principal,
    ).cancel_scheduled_draft(
        draft_id,
        expected_version=expected_version,
    )


@helpdesk_router.post("/drafts/{draft_id}/send", response_model=ReplyDraftRead)
async def send_reply_draft(
    draft_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    return await _service(db, principal).send_draft(draft_id)


@helpdesk_router.get("/reply-signatures", response_model=list[ReplySignatureRead])
async def list_reply_signatures(
    db: AsyncSession = Depends(get_db),
    principal=Depends(get_customer_service_principal),
):
    return await _service(db, principal).list_signatures()


@helpdesk_router.put("/reply-signatures/merchant", response_model=ReplySignatureRead)
async def put_merchant_reply_signature(
    payload: ReplySignatureWrite,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.settings.manage")),
):
    return await _service(db, principal).upsert_signature(user_id=None, payload=payload)


@helpdesk_router.put(
    "/reply-signatures/users/{user_id}", response_model=ReplySignatureRead
)
async def put_agent_reply_signature(
    user_id: UUID,
    payload: ReplySignatureWrite,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.settings.manage")),
):
    return await _service(db, principal).upsert_signature(
        user_id=user_id, payload=payload
    )


@helpdesk_router.patch("/customers/{customer_id}/custom-fields")
async def update_customer_custom_fields(
    customer_id: UUID,
    payload: CustomerCustomFieldsUpdate,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.customers.manage")),
):
    return await _service(db, principal).update_customer_custom_fields(
        customer_id, payload.custom_fields
    )


@helpdesk_router.get("/agents/productivity")
async def agent_productivity(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.analytics.read")),
):
    return await _service(db, principal).productivity(days=days)


__all__ = ["helpdesk_router"]
