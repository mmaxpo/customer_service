from __future__ import annotations

# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/conversation_intelligence.py
# ============================================================
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.schemas.conversation_intelligence import (
    ConversationInsightAnalyzeRequest,
    ConversationInsightRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.services.conversation_intelligence import (
    ConversationIntelligenceService,
)

conversation_intelligence_router = APIRouter(
    tags=["Customer Service - Conversation Intelligence"]
)


@conversation_intelligence_router.post(
    "/conversations/{conversation_id}/intelligence/analyze",
    response_model=ConversationInsightRead,
)
async def analyze_conversation(
    conversation_id: UUID,
    payload: ConversationInsightAnalyzeRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    force_refresh = payload.force_refresh if payload is not None else False

    result = await ConversationIntelligenceService(db).analyze(
        user_id=current_user.id,
        conversation_id=conversation_id,
        force_refresh=force_refresh,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return result


@conversation_intelligence_router.get(
    "/conversations/{conversation_id}/intelligence",
    response_model=list[ConversationInsightRead],
)
async def list_conversation_insights(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ConversationIntelligenceService(db).list_for_conversation(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/conversation_intelligence_snapshot.py
# ============================================================


from fastapi import APIRouter, Depends

from app.core.session import get_db
from app.domains.customer_service.schemas.conversation_intelligence_snapshot import (
    ConversationIntelligenceSnapshotRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.services.conversation_intelligence_snapshot import (
    ConversationIntelligenceSnapshotService,
)

conversation_intelligence_snapshot_router = APIRouter(
    tags=["Customer Service - Conversation Intelligence Snapshot"]
)


@conversation_intelligence_snapshot_router.get(
    "/conversations/{conversation_id}/intelligence/snapshot",
    response_model=ConversationIntelligenceSnapshotRead,
)
async def get_conversation_intelligence_snapshot(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ConversationIntelligenceSnapshotService(db).get_snapshot(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/suggested_actions.py
# ============================================================


from fastapi import APIRouter, Depends

from app.core.session import get_db
from app.domains.customer_service.schemas.suggested_actions import (
    ExecuteSuggestedActionRequest,
    SuggestedActionRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.services.suggested_actions import (
    SuggestedActionService,
)

suggested_actions_router = APIRouter(tags=["Customer Service - Suggested Actions"])


@suggested_actions_router.post(
    "/conversations/{conversation_id}/suggested-actions/generate",
    response_model=list[SuggestedActionRead],
)
async def generate(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await SuggestedActionService(db).generate(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )


@suggested_actions_router.get(
    "/conversations/{conversation_id}/suggested-actions",
    response_model=list[SuggestedActionRead],
)
async def list_actions(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await SuggestedActionService(db).list(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )


@suggested_actions_router.post(
    "/suggested-actions/{action_id}/accept",
    response_model=SuggestedActionRead,
)
async def accept_action(
    action_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await SuggestedActionService(db).accept(
        user_id=current_user.id,
        action_id=action_id,
    )


@suggested_actions_router.post(
    "/suggested-actions/{action_id}/reject",
    response_model=SuggestedActionRead,
)
async def reject_action(
    action_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await SuggestedActionService(db).reject(
        user_id=current_user.id,
        action_id=action_id,
    )


@suggested_actions_router.post(
    "/suggested-actions/{action_id}/execute",
    response_model=SuggestedActionRead,
)
async def execute_action(
    action_id: UUID,
    payload: ExecuteSuggestedActionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await SuggestedActionService(db).execute(
        user_id=current_user.id,
        action_id=action_id,
        payload=payload.payload if payload else None,
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/reply_quality.py
# ============================================================


from fastapi import APIRouter, Depends

from app.core.session import get_db
from app.domains.customer_service.schemas.reply_quality import (
    ReplyQualityAnalyticsRead,
    ReplyQualityCreate,
    ReplyQualityRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.services.reply_quality import ReplyQualityService

reply_quality_router = APIRouter(tags=["Customer Service - Reply Quality"])


@reply_quality_router.post(
    "/conversations/{conversation_id}/reply-quality",
    response_model=ReplyQualityRead,
)
async def record_reply_quality(
    conversation_id: UUID,
    payload: ReplyQualityCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ReplyQualityService(db).record_review(
        user_id=current_user.id,
        conversation_id=conversation_id,
        reply_message_id=payload.reply_message_id,
        outcome=payload.outcome,
        score=payload.score,
        accuracy_score=payload.accuracy_score,
        relevance_score=payload.relevance_score,
        tone_score=payload.tone_score,
        draft_body=payload.draft_body,
        final_body=payload.final_body,
        reviewer_id=getattr(current_user, "actor_user_id", current_user.id),
    )


@reply_quality_router.get(
    "/conversations/{conversation_id}/reply-quality",
    response_model=list[ReplyQualityRead],
)
async def list_reply_quality(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ReplyQualityService(db).list_for_conversation(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )


@reply_quality_router.get(
    "/analytics/reply-quality",
    response_model=ReplyQualityAnalyticsRead,
)
async def reply_quality_analytics(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ReplyQualityService(db).analytics(user_id=current_user.id)


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/quality_reviews.py
# ============================================================


from fastapi import APIRouter, Depends

from app.core.session import get_db
from app.domains.customer_service.schemas.quality_reviews import QualityReviewRead
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.services.quality_reviews import QualityReviewService

quality_reviews_router = APIRouter(tags=["Customer Service Quality Reviews"])


@quality_reviews_router.post(
    "/conversations/{conversation_id}/quality-review", response_model=QualityReviewRead
)
async def review(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):

    return await QualityReviewService(db).review(
        user_id=current_user.id, conversation_id=conversation_id
    )


@quality_reviews_router.get(
    "/conversations/{conversation_id}/quality-review",
    response_model=list[QualityReviewRead],
)
async def list_reviews(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):

    return await QualityReviewService(db).list(
        user_id=current_user.id, conversation_id=conversation_id
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/ai_replies.py
# ============================================================


from fastapi import APIRouter, Depends

from app.core.session import get_db
from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.schemas.ai_replies import (
    AIReplyComposeRead,
    AIReplyComposeRequest,
)
from app.domains.customer_service.schemas.ai_reply_regenerate import (
    AIReplyRegenerateRead,
)
from app.domains.customer_service.schemas.conversation_summary import (
    ConversationSummaryRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.services.ai_replies import AIReplyService
from app.domains.customer_service.services.ai_reply_regeneration import (
    AIReplyRegenerationService,
)
from app.domains.customer_service.services.conversation_summary import (
    ConversationSummaryService,
)

ai_replies_router = APIRouter(tags=["Customer Service - AI Replies"])


@ai_replies_router.post(
    "/conversations/{conversation_id}/ai-replies/compose",
    response_model=AIReplyComposeRead,
)
async def compose_ai_reply(
    conversation_id: UUID,
    payload: AIReplyComposeRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payload = payload or AIReplyComposeRequest()

    return await AIReplyService(db).compose_for_conversation(
        user_id=current_user.id,
        conversation_id=conversation_id,
        customer_message=payload.customer_message,
        shopify_context=payload.shopify_context,
        force_refresh_intelligence=payload.force_refresh_intelligence,
    )


@ai_replies_router.post(
    "/conversations/{conversation_id}/ai-replies/regenerate",
    response_model=AIReplyRegenerateRead,
)
async def regenerate_ai_reply(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conversation_repo = ConversationRepository(db)

    conversation = await conversation_repo.get_detail(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )

    latest_customer_message = await conversation_repo.get_latest_customer_message(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )

    return await AIReplyRegenerationService(db).regenerate(
        user_id=current_user.id,
        conversation=conversation,
        customer_message=latest_customer_message.body
        if latest_customer_message
        else "",
    )


@ai_replies_router.post(
    "/conversations/{conversation_id}/summary/generate",
    response_model=ConversationSummaryRead,
)
async def generate_conversation_summary(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conversation = await ConversationRepository(db).get_detail(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )

    return await ConversationSummaryService(db).generate(
        user_id=current_user.id,
        conversation=conversation,
    )


__all__ = [
    "conversation_intelligence_router",
    "conversation_intelligence_snapshot_router",
    "suggested_actions_router",
    "reply_quality_router",
    "quality_reviews_router",
    "ai_replies_router",
]
