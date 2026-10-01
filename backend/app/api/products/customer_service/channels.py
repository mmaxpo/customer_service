from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import logging
import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import SessionLocal, get_db
from app.domains.customer_service.services.assignment_rules import AssignmentRulesService
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
    CustomerSupportOrchestrationResult,
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
    current_user=Depends(require_customer_service_permission("cs.settings.manage")),
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
        "self_service": _self_service(settings),
        "logo": _logo(settings),
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


async def _analyze_conversation(user_id: UUID, conversation_id: UUID) -> None:
    """Record the conversation's topic (intent) for the inbox, Live and Desk.
    Runs after the response so the customer's reply is never delayed."""
    from app.domains.customer_service.services.conversation_intelligence import (
        ConversationIntelligenceService,
    )

    try:
        async with SessionLocal() as db:
            await ConversationIntelligenceService(db).analyze(
                user_id=user_id, conversation_id=conversation_id
            )
            # The topic is known now: give the conversation to a team member
            # if the routing rules say so.
            await AssignmentRulesService(db).assign(
                workspace_id=user_id, conversation_id=conversation_id
            )
    except Exception:
        logging.getLogger(__name__).exception(
            "Conversation analysis failed for %s", conversation_id
        )


@chat_router.post("/public/{public_key}/sessions/{session_id}/messages")
async def create_public_message(
    public_key: str,
    session_id: UUID,
    payload: ChatMessageCreateRequest,
    background_tasks: BackgroundTasks,
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
            "customer_email": session.customer_email,
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

    # Once a team member has replied, the conversation is theirs: no automated
    # reply until the case is resolved.
    team_is_handling = inbox_message is not None and bool(
        await db.scalar(
            text(
                """
                SELECT EXISTS (
                  SELECT 1 FROM cs_conversation_messages m
                  WHERE m.conversation_id = :conversation_id
                    AND m.sender_type = 'agent'
                    AND m.created_at > coalesce(
                      (SELECT max(t.resolved_at) FROM cs_tickets t
                        WHERE t.conversation_id = :conversation_id),
                      '-infinity'::timestamptz)
                )
                """
            ),
            {"conversation_id": inbox_message.conversation_id},
        )
    )

    if team_is_handling:
        orchestration = CustomerSupportOrchestrationResult(
            handled=True,
            dispatch_skip_reason="team_member_is_handling",
        )
    else:
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
                "Thanks. I've passed your request to our team. They'll review it "
                "and reply here. Nothing on your order has been changed yet."
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

    if inbox_message is not None:
        background_tasks.add_task(
            _analyze_conversation, settings.user_id, inbox_message.conversation_id
        )

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


SELF_SERVICE_REQUESTS = {
    "report_problem": "Report a problem",
    "start_return": "Start a return",
}


def _self_service(settings) -> dict[str, bool]:
    """Self-service buttons the merchant switched on (Settings → Chat widget)."""
    chosen = (settings.meta or {}).get("self_service") or {}
    return {
        key: bool(chosen.get(key))
        for key in ("track_order", *SELF_SERVICE_REQUESTS)
    }


def _logo(settings) -> str | None:
    """The merchant's logo (an uploaded image stored as a data URL), if any."""
    logo = (settings.meta or {}).get("logo")
    if isinstance(logo, str) and re.match(r"data:image/(png|jpeg|webp);base64,", logo):
        return logo
    return None


def _order_ref(order_number: str) -> str:
    return "#" + order_number.strip().lstrip("#").strip()


class TrackOrderRequest(BaseModel):
    order_number: str = Field(min_length=1, max_length=40)
    email: str = Field(min_length=3, max_length=320)


class SelfServiceRequest(BaseModel):
    kind: str
    order_number: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=2000)


@chat_router.post("/public/{public_key}/sessions/{session_id}/track-order")
async def track_order(
    public_key: str,
    session_id: UUID,
    payload: TrackOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Order status straight from Shopify, no AI. Shared only when the order
    number and the email it was placed with both match; a wrong number and a
    wrong email get the same answer."""
    session = await _public_session(db, public_key, session_id)
    settings = await build_service(db).get_widget_settings_by_public_key(
        public_key=public_key
    )
    if not _self_service(settings)["track_order"]:
        raise HTTPException(status_code=404, detail="Order tracking is not enabled")

    order = await build_application_runtime_services(
        db=db, user_id=session.user_id
    ).capabilities.invoke(
        "shopify.get_order",
        user_id=session.user_id,
        payload={"order_ref": _order_ref(payload.order_number)},
    )

    order_email = str(order.get("customer_email") or "").strip().lower()
    if not order.get("order_id") or not order_email or order_email != payload.email.strip().lower():
        return {"found": False}

    summary = order.get("summary") or {}
    return {
        "found": True,
        "order_name": order.get("order_name"),
        "paid": bool(summary.get("is_paid")),
        "shipped": bool(summary.get("is_fulfilled")),
        "carrier": summary.get("carrier"),
        "tracking_number": summary.get("tracking_number"),
        "tracking_url": summary.get("tracking_url"),
    }


@chat_router.post("/public/{public_key}/sessions/{session_id}/requests")
async def self_service_request(
    public_key: str,
    session_id: UUID,
    payload: SelfServiceRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Problem reports and returns go straight to the team: no automation runs."""
    session = await _public_session(db, public_key, session_id)
    service = build_service(db)
    settings = await service.get_widget_settings_by_public_key(public_key=public_key)
    if not _self_service(settings).get(payload.kind):
        raise HTTPException(status_code=404, detail="This request type is not enabled")

    message = await service.add_customer_message(
        session_id=session.id,
        content=(
            f"{SELF_SERVICE_REQUESTS[payload.kind]}: order {_order_ref(payload.order_number)}\n"
            f"{payload.description.strip()}"
        ),
    )
    inbox_message = await service.add_inbox_customer_message_for_chat_session(
        session=session, chat_message=message
    )
    reply = await service.add_ai_message(
        session_id=session.id,
        content=(
            "Thanks. I've passed your request to our team. They'll review it "
            "and reply here. Nothing on your order has been changed yet."
        ),
    )
    await service.add_inbox_ai_message_for_chat_session(session=session, chat_message=reply)
    await service.commit()

    if inbox_message is not None:
        background_tasks.add_task(
            _analyze_conversation, session.user_id, inbox_message.conversation_id
        )
    return {"ok": True}


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
