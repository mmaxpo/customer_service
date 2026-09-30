from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.services.customer_feedback import CustomerFeedbackService
from app.domains.customer_service.integrations.omnichannel.providers import (
    register_default_omnichannel_providers,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)
from app.domains.customer_service.providers.commerce_defaults import (
    build_default_commerce_order_adapter_registry,
)
from app.domains.customer_service.repositories.chat_repository import ChatRepository
from app.domains.customer_service.schemas.chat import (
    ChatMessageCreateRequest,
    ChatSessionCreateRequest,
    ChatWidgetSettingsUpdateRequest,
)
from app.domains.customer_service.schemas.omnichannel import (
    ChannelConnectionCreate,
    ChannelConnectionRead,
    OmnichannelDeliveryEvent,
    OmnichannelDeliveryEventResult,
    OmnichannelInboundMessage,
    OmnichannelInboundResult,
    OmnichannelOutboundDeliveryJobEnqueueResult,
    OmnichannelOutboundMessage,
    OmnichannelOutboundResult,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
    require_customer_service_permission,
)
from app.domains.customer_service.services.chat_service import CustomerChatService
from app.domains.customer_service.services.support.commerce.customer_support_commerce_context import (
    CustomerSupportCommerceContextService,
)
from app.domains.customer_service.services.support.customer_support_orchestration import (
    CustomerSupportOrchestrationService,
)
from app.domains.customer_service.services.event_subscriptions import (
    CustomerServiceEventSubscriptionService,
)
from app.domains.customer_service.services.omnichannel import (
    CustomerServiceOmnichannelService,
)
from app.domains.customer_service.workflows.message_classifier import (
    CustomerServiceMessageClassifier,
)
from app.platform.events.publisher import PlatformEventPublisher
from app.runtime_services import build_application_runtime_services
from app.tenancy.models import Workspace
from app.tenancy.working_calendar import operating_state, resolved_workspace_calendar

# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/channels.py
# ============================================================


channels_router = APIRouter(tags=["Customer Service - Channels"])


@channels_router.get("/")
async def get_channels():
    return {"channels": ["email", "website_chat"]}


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/chat_router.py
# ============================================================


chat_router = APIRouter(
    prefix="/chat",
    tags=["Customer Chat"],
)


def build_service(
    db: AsyncSession,
) -> CustomerChatService:
    return CustomerChatService(ChatRepository(db))


@chat_router.post("/sessions")
async def create_session(
    payload: ChatSessionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = build_service(db)

    session = await service.create_session(
        user_id=current_user.id,
        visitor_id=payload.visitor_id,
        channel=payload.channel,
    )

    await service.commit()

    return {
        "id": str(session.id),
        "visitor_id": session.visitor_id,
        "channel": session.channel,
    }


@chat_router.post("/sessions/{session_id}/messages")
async def create_message(
    session_id: UUID,
    payload: ChatMessageCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = build_service(db)

    session = await service.get_session(session_id=session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    message = await service.add_customer_message(
        session_id=session_id,
        content=payload.content,
    )

    await service.commit()

    return {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
    }


@chat_router.get("/sessions/{session_id}/messages")
async def list_messages(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = build_service(db)

    session = await service.get_session(session_id=session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = await service.get_messages(
        session_id=session_id,
    )

    print(
        "PUBLIC CHAT MESSAGE COUNT",
        len(messages),
    )

    for m in messages:
        print(
            "PUBLIC CHAT",
            m.role,
            m.content,
        )

    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at,
        }
        for m in messages
    ]


@chat_router.get("/widget/settings")
async def get_widget_settings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = build_service(db)

    settings = await service.get_or_create_widget_settings(
        user_id=current_user.id,
    )

    await service.commit()

    return settings


@chat_router.put("/widget/settings")
async def update_widget_settings(
    payload: ChatWidgetSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = build_service(db)

    values = payload.model_dump(exclude_unset=True)

    settings = await service.update_widget_settings(
        user_id=current_user.id,
        values=values,
    )

    if "workflow_template_id" in values or "auto_answer_enabled" in values:
        await CustomerServiceEventSubscriptionService(
            db
        ).upsert_website_chat_automation_subscription(
            user_id=current_user.id,
            workflow_template_id=settings.workflow_template_id,
            enabled=settings.auto_answer_enabled,
        )

    await service.commit()

    return settings


@chat_router.get("/public/{public_key}/settings")
async def get_public_widget_settings(
    public_key: str,
    db: AsyncSession = Depends(get_db),
):
    service = build_service(db)

    settings = await service.get_widget_settings_by_public_key(
        public_key=public_key,
    )

    if settings is None or not settings.enabled:
        raise HTTPException(status_code=404, detail="Chat widget not found")

    workspace = await db.get(Workspace, settings.user_id)
    # Legacy installations without a workspace row retain their previous
    # always-available behavior; normal tenants always resolve a workspace.
    calendar = resolved_workspace_calendar(
        timezone_name=workspace.timezone if workspace else "UTC",
        business_hours=workspace.business_hours if workspace else None,
    )
    state = operating_state(datetime.now(timezone.utc), calendar)

    return {
        "public_key": settings.public_key,
        "enabled": settings.enabled,
        "title": settings.title,
        "welcome_message": settings.welcome_message,
        "brand_color": settings.brand_color,
        "position": settings.position,
        "assistant_name": settings.assistant_name,
        "auto_answer_enabled": settings.auto_answer_enabled,
        "auto_answer_confidence_threshold": settings.auto_answer_confidence_threshold,
        "human_handoff_enabled": settings.human_handoff_enabled,
        "human_handoff_message": settings.human_handoff_message,
        "operating_state": state,
        "is_within_business_hours": state == "open",
    }


@chat_router.post("/public/{public_key}/sessions")
async def create_public_session(
    public_key: str,
    payload: ChatSessionCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    service = build_service(db)

    settings = await service.get_widget_settings_by_public_key(
        public_key=public_key,
    )

    if settings is None or not settings.enabled:
        raise HTTPException(status_code=404, detail="Chat widget not found")

    session = await service.create_session(
        user_id=settings.user_id,
        visitor_id=payload.visitor_id,
        channel=payload.channel,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
    )

    bridge = await service.ensure_inbox_bridge_for_session(
        session=session,
    )

    await service.commit()

    return {
        "id": str(session.id),
        "visitor_id": session.visitor_id,
        "channel": session.channel,
        "conversation_id": str(bridge.conversation_id),
        "ticket_id": str(bridge.ticket_id),
    }


@chat_router.post("/public/{public_key}/sessions/{session_id}/messages")
async def create_public_message(
    public_key: str,
    session_id: UUID,
    payload: ChatMessageCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    service = build_service(db)

    settings = await service.get_widget_settings_by_public_key(
        public_key=public_key,
    )

    if settings is None or not settings.enabled:
        raise HTTPException(status_code=404, detail="Chat widget not found")

    session = await service.get_session(session_id=session_id)
    if session is None or session.user_id != settings.user_id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    if payload.client_message_id:
        await service.acquire_public_ingress_lock(
            session_id=session_id,
            client_message_id=payload.client_message_id,
        )

        existing_message = await service.get_message_by_client_message_id(
            session_id=session_id,
            client_message_id=payload.client_message_id,
        )

        if existing_message is not None:
            public_ingress = (existing_message.meta or {}).get("public_ingress") or {}

            if public_ingress:
                return {
                    "id": str(existing_message.id),
                    "role": existing_message.role,
                    "content": existing_message.content,
                    "created_at": existing_message.created_at,
                    "conversation_id": public_ingress.get("conversation_id"),
                    "inbox_message_id": public_ingress.get("inbox_message_id"),
                    "event_id": public_ingress.get("event_id"),
                    "workflow_dispatch": public_ingress.get("workflow_dispatch")
                    or {
                        "matched": 0,
                        "enqueued": [],
                        "skipped": [],
                    },
                    "support_intake": public_ingress.get("support_intake"),
                    "idempotent_replay": True,
                }

    message = await service.add_customer_message(
        session_id=session_id,
        content=payload.content,
        client_message_id=payload.client_message_id,
    )

    inbox_message = await service.add_inbox_customer_message_for_chat_session(
        session=session,
        chat_message=message,
    )

    published = await PlatformEventPublisher(db).publish(
        user_id=settings.user_id,
        event_type="customer.chat.message.created",
        source="customer_service.chat",
        payload={
            "session_id": str(session.id),
            "message_id": str(message.id),
            "conversation_id": (
                str(inbox_message.conversation_id)
                if inbox_message is not None
                else None
            ),
            "inbox_message_id": (
                str(inbox_message.id) if inbox_message is not None else None
            ),
            "visitor_id": session.visitor_id,
            "channel": session.channel,
            "body": message.content,
            "role": message.role,
            "public_key": settings.public_key,
            "widget": {
                "auto_answer_enabled": settings.auto_answer_enabled,
                "workflow_template_id": (
                    str(settings.workflow_template_id)
                    if settings.workflow_template_id is not None
                    else None
                ),
                "auto_answer_confidence_threshold": settings.auto_answer_confidence_threshold,
                "human_handoff_enabled": settings.human_handoff_enabled,
                "human_handoff_message": settings.human_handoff_message,
            },
        },
        meta={
            "chat_widget": True,
        },
        dispatch=False,
        commit=False,
    )

    runtime_services = build_application_runtime_services(
        db=db,
        user_id=settings.user_id,
    )

    orchestration = await CustomerSupportOrchestrationService(
        db=db,
        chat_service=service,
        commerce_context=CustomerSupportCommerceContextService(
            capabilities=runtime_services.capabilities,
            commerce_adapters=(
                build_default_commerce_order_adapter_registry()
            ),
        ),
    ).handle(
        user_id=settings.user_id,
        session=session,
        message=message,
    )

    support_intake = orchestration.support_intake

    classification = CustomerServiceMessageClassifier().classify(message.content)

    # Do not let a merchant's single attached order-status workflow answer a
    # risky request such as cancellation or a damaged-item report. Those
    # intents must remain in the human-review lane until their dedicated
    # approval workflow is selected. Give the customer a truthful handoff
    # instead of running an unrelated workflow.
    safe_handoff_intents = {"cancellation", "damaged_product"}
    if not orchestration.handled and classification.intent in safe_handoff_intents:
        handoff_message = await service.add_ai_message(
            session_id=session.id,
            content=(
                "I can help with that request. A support agent will review it "
                "before any Shopify action is taken. No Shopify action has been performed."
            ),
        )
        await service.add_inbox_ai_message_for_chat_session(
            session=session,
            chat_message=handoff_message,
        )
        orchestration = type(orchestration)(
            handled=True,
            support_intake=orchestration.support_intake,
            dispatch_skip_reason="risky_intent_requires_human_review",
        )

    if orchestration.handled:
        workflow_dispatch = {
            "matched": 0,
            "filter_matched": 0,
            "selected": 0,
            "enqueued": [],
            "skipped": [
                {
                    "reason": orchestration.dispatch_skip_reason,
                }
            ],
            "classification": classification.model_dump(),
        }
    else:
        workflow_dispatch = await CustomerServiceEventSubscriptionService(
            db
        ).enqueue_matching_workflows_for_event(
            event=published["event"],
            commit=False,
        )

    response_payload = {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
        "conversation_id": (
            str(inbox_message.conversation_id) if inbox_message is not None else None
        ),
        "inbox_message_id": (
            str(inbox_message.id) if inbox_message is not None else None
        ),
        "event_id": str(published["event"].id),
        "workflow_dispatch": workflow_dispatch,
        "support_intake": support_intake,
    }

    if payload.client_message_id:
        await service.save_public_ingress_result(
            message=message,
            result={
                "conversation_id": response_payload["conversation_id"],
                "inbox_message_id": response_payload["inbox_message_id"],
                "event_id": response_payload["event_id"],
                "workflow_dispatch": workflow_dispatch,
                "support_intake": support_intake,
            },
        )

    await service.commit()

    return {
        **response_payload,
        "idempotent_replay": False,
    }


@chat_router.get("/public/{public_key}/sessions/{session_id}/messages")
async def list_public_messages(
    public_key: str,
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = build_service(db)

    settings = await service.get_widget_settings_by_public_key(
        public_key=public_key,
    )

    if settings is None or not settings.enabled:
        raise HTTPException(status_code=404, detail="Chat widget not found")

    session = await service.get_session(session_id=session_id)
    if session is None or session.user_id != settings.user_id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = await service.get_messages(
        session_id=session_id,
    )

    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at,
            "feedback": m.meta.get("customer_feedback") if isinstance(m.meta, dict) else None,
        }
        for m in messages
    ]


async def _public_session(db: AsyncSession, public_key: str, session_id: UUID):
    service = build_service(db)
    settings = await service.get_widget_settings_by_public_key(public_key=public_key)
    if settings is None or not settings.enabled:
        raise HTTPException(status_code=404, detail="Chat widget not found")
    session = await service.get_session(session_id=session_id)
    if session is None or session.user_id != settings.user_id:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


class AnswerFeedbackRequest(BaseModel):
    helpful: bool


class ChatRatingRequest(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


@chat_router.post("/public/{public_key}/sessions/{session_id}/messages/{message_id}/feedback")
async def answer_feedback(
    public_key: str,
    session_id: UUID,
    message_id: UUID,
    payload: AnswerFeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    session = await _public_session(db, public_key, session_id)
    return await CustomerFeedbackService(db).answer_feedback(
        workspace_id=session.user_id,
        session_id=session.id,
        message_id=message_id,
        helpful=payload.helpful,
    )


@chat_router.post("/public/{public_key}/sessions/{session_id}/rating")
async def rate_chat(
    public_key: str,
    session_id: UUID,
    payload: ChatRatingRequest,
    db: AsyncSession = Depends(get_db),
):
    session = await _public_session(db, public_key, session_id)
    return await CustomerFeedbackService(db).rate_chat(
        workspace_id=session.user_id,
        session_id=session.id,
        score=payload.score,
        comment=(payload.comment or "").strip() or None,
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/omnichannel.py
# ============================================================


omnichannel_router = APIRouter(tags=["Customer Service - Omnichannel"])


@omnichannel_router.get("/connections", response_model=list[ChannelConnectionRead])
async def list_channel_connections(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceOmnichannelService(db).list_connections(current_user.id)


@omnichannel_router.post("/connections", response_model=ChannelConnectionRead)
async def create_channel_connection(
    payload: ChannelConnectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.integrations.manage")),
):
    service = CustomerServiceOmnichannelService(db)
    result = await service.create_connection(
        user_id=current_user.id,
        payload=payload,
    )
    await service.commit()
    return result


@omnichannel_router.post("/inbound", response_model=OmnichannelInboundResult)
async def ingest_inbound_message(
    payload: OmnichannelInboundMessage,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = CustomerServiceOmnichannelService(db)
    result = await service.ingest_inbound_message(
        user_id=current_user.id,
        payload=payload,
    )

    await service.commit()
    return result


@omnichannel_router.post("/outbound", response_model=OmnichannelOutboundResult)
async def send_outbound_message(
    payload: OmnichannelOutboundMessage,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = CustomerServiceOmnichannelService(db)
    result = await service.send_outbound_message(
        user_id=current_user.id,
        payload=payload,
    )
    await service.commit()
    return result


@omnichannel_router.post(
    "/delivery-events", response_model=OmnichannelDeliveryEventResult
)
async def apply_delivery_event(
    payload: OmnichannelDeliveryEvent,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = CustomerServiceOmnichannelService(db)
    result = await service.apply_delivery_event(
        user_id=current_user.id,
        payload=payload,
    )
    await service.commit()
    return result


@omnichannel_router.get("/providers/capabilities")
async def list_provider_capabilities():
    register_default_omnichannel_providers()
    registry = get_omnichannel_provider_registry()

    production_capabilities = []
    for adapter in registry.list():
        capabilities = adapter.capabilities()
        production_ready = (
            capabilities.get("production_ready", False)
            if isinstance(capabilities, dict)
            else capabilities.production_ready
        )
        if production_ready:
            production_capabilities.append(capabilities)
    return production_capabilities


@omnichannel_router.post(
    "/outbound/enqueue", response_model=OmnichannelOutboundDeliveryJobEnqueueResult
)
async def enqueue_outbound_message(
    payload: OmnichannelOutboundMessage,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceOmnichannelService(db).enqueue_outbound_delivery(
        user_id=current_user.id,
        payload=payload,
    )


__all__ = [
    "channels_router",
    "chat_router",
    "omnichannel_router",
]
