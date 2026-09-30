from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.core.config import settings
from app.domains.customer_service.schemas.commercial import (
    ConversationSplitRequest,
    ConversationFollowerRead,
    CSATResponse,
    CustomerConsentUpdate,
    LeaseRequest,
    MergeRequest,
    NotificationCreate,
    OnboardingUpdate,
    PrivacyRequestCreate,
    ResolutionRequest,
    SavedViewCreate,
    SLACalendarCreate,
)
from app.domains.customer_service.schemas.billing import (
    ShopifyBillingCheckoutRead,
    ShopifyBillingCheckoutRequest,
    ShopifyBillingPortalRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
    require_customer_service_permission,
)
from app.domains.customer_service.services.billing import BillingWebhookService
from app.domains.customer_service.services.shopify_billing import ShopifyBillingService
from app.domains.customer_service.services.commercial_operations import (
    CommercialOperationsService,
)


router = APIRouter(tags=["Customer Service - Commercial Operations"])


def _service(db, principal) -> CommercialOperationsService:
    return CommercialOperationsService(
        db,
        workspace_id=principal.id,
        actor_id=getattr(principal, "actor_user_id", principal.id),
    )


async def _read_limited_upload(upload: UploadFile) -> bytes:
    chunks = []
    size = 0
    while chunk := await upload.read(64 * 1024):
        size += len(chunk)
        if size > settings.MAX_ATTACHMENT_BYTES:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=413, detail="Attachment size is not allowed"
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.get("/search")
async def search_conversations(
    q: str | None = Query(default=None, max_length=255),
    channel: str | None = None,
    conversation_status: str | None = Query(default=None, alias="status"),
    assigned_to: str | None = None,
    unassigned: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await _service(db, current_user).search_conversations(
        query=q,
        channel=channel,
        status=conversation_status,
        assigned_to=assigned_to,
        unassigned=unassigned,
        limit=limit,
        offset=offset,
    )


@router.post("/saved-views", status_code=201)
async def create_saved_view(
    payload: SavedViewCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = _service(db, current_user)
    await service.require_entitlement("saved_views")
    return await service.create_saved_view(payload)


@router.get("/saved-views")
async def list_saved_views(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await _service(db, current_user).list_saved_views()


@router.delete("/saved-views/{view_id}", status_code=204)
async def delete_saved_view(
    view_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await _service(db, current_user).delete_saved_view(view_id)
    return Response(status_code=204)


@router.post("/conversations/{conversation_id}/attachments", status_code=201)
async def upload_attachment(
    conversation_id: UUID,
    upload: UploadFile = File(...),
    message_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = _service(db, current_user)
    await service.require_entitlement("attachments")
    return await service.store_attachment(
        conversation_id=conversation_id,
        filename=upload.filename or "attachment",
        content_type=upload.content_type or "application/octet-stream",
        content=await _read_limited_upload(upload),
        message_id=message_id,
    )


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    attachment, path, signed = await _service(db, current_user).get_attachment(
        attachment_id
    )
    if signed:
        return RedirectResponse(str(path), status_code=307)
    return FileResponse(
        path, media_type=attachment.content_type, filename=attachment.filename
    )


@router.get(
    "/conversations/{conversation_id}/followers",
    response_model=list[ConversationFollowerRead],
)
async def list_conversation_followers(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await _service(
        db,
        current_user,
    ).list_conversation_followers(conversation_id)


@router.put(
    "/conversations/{conversation_id}/followers/{user_id}",
    response_model=ConversationFollowerRead,
)
async def follow_conversation(
    conversation_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    return await _service(
        db,
        current_user,
    ).follow_conversation(
        conversation_id,
        user_id,
    )


@router.delete(
    "/conversations/{conversation_id}/followers/{user_id}",
    status_code=204,
)
async def unfollow_conversation(
    conversation_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    await _service(
        db,
        current_user,
    ).unfollow_conversation(
        conversation_id,
        user_id,
    )

    return Response(status_code=204)


@router.post("/conversations/{conversation_id}/presence")
async def acquire_presence(
    conversation_id: UUID,
    payload: LeaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await _service(db, current_user).acquire_lease(
        conversation_id, payload.ttl_seconds
    )


@router.delete("/conversations/{conversation_id}/presence", status_code=204)
async def release_presence(
    conversation_id: UUID,
    lease_token: str = Header(alias="x-conversation-lease"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await _service(db, current_user).release_lease(conversation_id, lease_token)
    return Response(status_code=204)


@router.post("/notifications", status_code=201)
async def create_notification(
    payload: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    return await _service(db, current_user).create_notification(payload)


@router.get("/notifications")
async def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await _service(db, current_user).list_notifications(unread_only, limit)


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await _service(db, current_user).read_notification(notification_id)


@router.post("/sla/calendars", status_code=201)
async def create_sla_calendar(
    payload: SLACalendarCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.sla.manage")),
):
    return await _service(db, current_user).create_sla_calendar(payload)


@router.get("/sla/calendars")
async def list_sla_calendars(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.sla.read")),
):
    return await _service(db, current_user).list_sla_calendars()


@router.get("/sla/calendars/{calendar_id}/due-at")
async def calculate_sla_due_at(
    calendar_id: UUID,
    start: datetime,
    minutes: int = Query(ge=1, le=525_600),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.sla.read")),
):
    due_at = await _service(db, current_user).calculate_sla_due_at(
        calendar_id, start, minutes
    )
    return {"due_at": due_at}


@router.post("/customers/merge")
async def merge_customers(
    payload: MergeRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.settings.manage")),
):
    return await _service(db, current_user).merge_customers(
        payload.source_id, payload.target_id
    )


@router.post("/conversations/merge")
async def merge_conversations(
    payload: MergeRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.settings.manage")),
):
    return await _service(db, current_user).merge_conversations(
        payload.source_id, payload.target_id
    )


@router.post("/conversations/{conversation_id}/split")
async def split_conversation(
    conversation_id: UUID,
    payload: ConversationSplitRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.settings.manage")),
):
    return await _service(db, current_user).split_conversation(conversation_id, payload)


@router.post("/tickets/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: UUID,
    payload: ResolutionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await _service(db, current_user).resolve_ticket(ticket_id, payload)


@router.post("/csat/respond")
async def respond_to_csat(payload: CSATResponse, db: AsyncSession = Depends(get_db)):
    return await CommercialOperationsService(db, workspace_id=UUID(int=0)).answer_csat(
        payload.token, payload.score, payload.comment
    )


@router.get("/csat/report")
async def csat_report(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await _service(db, current_user).csat_report()


@router.get("/onboarding")
async def get_onboarding(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await _service(db, current_user).onboarding()


@router.patch("/onboarding")
async def update_onboarding(
    payload: OnboardingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.settings.manage")),
):
    return await _service(db, current_user).update_onboarding(payload.checklist)


@router.post("/onboarding/demo-data", status_code=201)
async def seed_onboarding_demo_data(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.settings.manage")),
):
    return await _service(db, current_user).seed_demo_data()


@router.patch("/customers/{customer_id}/consent")
async def update_customer_consent(
    customer_id: UUID,
    payload: CustomerConsentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.customers.manage")),
):
    return await _service(db, current_user).update_customer_consent(
        customer_id, payload.model_dump()
    )


@router.get("/provider-health")
async def provider_health(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await _service(db, current_user).provider_health()


@router.get("/subscription")
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.billing.read")),
):
    return await _service(db, current_user).subscription()


@router.post(
    "/billing/shopify/checkout",
    response_model=ShopifyBillingCheckoutRead,
)
async def create_shopify_billing_checkout(
    payload: ShopifyBillingCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.billing.manage")),
):
    return await ShopifyBillingService(db).checkout(
        workspace_id=current_user.id,
        plan=payload.plan,
    )


@router.post("/billing/shopify/sync")
async def sync_shopify_billing(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.billing.manage")),
):
    return await ShopifyBillingService(db).sync(workspace_id=current_user.id)


@router.delete("/billing/shopify/subscription")
async def cancel_shopify_billing(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.billing.manage")),
):
    return await ShopifyBillingService(db).cancel(workspace_id=current_user.id)


@router.get("/billing/shopify/portal", response_model=ShopifyBillingPortalRead)
async def get_shopify_billing_portal(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.billing.read")),
):
    return await ShopifyBillingService(db).portal(workspace_id=current_user.id)


@router.post("/billing/webhook")
async def billing_webhook(
    request: Request,
    timestamp: str = Header(alias="x-billing-timestamp"),
    signature: str = Header(alias="x-billing-signature"),
    db: AsyncSession = Depends(get_db),
):
    return await BillingWebhookService(db).apply(
        raw_body=await request.body(), timestamp=timestamp, signature=signature
    )


@router.post("/privacy/requests", status_code=201)
async def create_privacy_request(
    payload: PrivacyRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.privacy.manage")),
):
    return await _service(db, current_user).privacy_request(
        payload.customer_id, payload.kind
    )


@router.get("/privacy/requests")
async def list_privacy_requests(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.privacy.manage")),
):
    return await _service(db, current_user).list_privacy_requests()


@router.get("/privacy/retention-preview")
async def preview_privacy_retention(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.privacy.manage")),
):
    return await _service(db, current_user).retention_preview(limit=limit)


__all__ = ["router"]
