from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.services.ai_context_policy import (
    CustomerServiceAIContextPolicy,
)
from app.domains.customer_service.models import (
    CustomerServiceQualityReview,
    SLAViolation,
    TicketAssignment,
)
from app.domains.customer_service.services.inbox import InboxService
from app.domains.customer_service.services.tags import ConversationTagService
from app.domains.customer_service.services.conversation_intelligence import (
    ConversationIntelligenceService,
)
from app.domains.customer_service.services.suggested_actions import (
    SuggestedActionService,
)
from app.domains.customer_service.services.workflow_executions import (
    CustomerServiceWorkflowExecutionService,
)
from app.domains.customer_service.services.timeline import ConversationTimelineService


class ConversationContextService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.context_policy = CustomerServiceAIContextPolicy.from_env()
        self.conversation_repo = ConversationRepository(db)

    async def get_context(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
    ) -> dict:
        conversation = await InboxService(self.db).get_conversation_detail(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        ticket = getattr(conversation, "ticket", None)

        tags = await ConversationTagService(self.db).list_tags(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        insights = await ConversationIntelligenceService(self.db).list_for_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        suggested_actions = await SuggestedActionService(self.db).list(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        workflow_executions = await CustomerServiceWorkflowExecutionService(
            self.db
        ).list(
            user_id=user_id,
            conversation_id=conversation_id,
            limit=100,
            offset=0,
        )

        timeline = await ConversationTimelineService(self.db).get_timeline(
            user_id=user_id,
            conversation_id=conversation_id,
            limit=200,
        )

        assignments = []
        sla_violations = []

        if ticket is not None:
            assignments = await self._list_assignments(
                user_id=user_id,
                ticket_id=ticket.id,
            )
            sla_violations = await self._list_sla_violations(
                user_id=user_id,
                ticket_id=ticket.id,
            )

        quality_reviews = await self._list_quality_reviews(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        encoded_insights = jsonable_encoder(insights)

        recent_messages = (
            await self.conversation_repo.list_recent_context_messages(
                user_id=user_id,
                conversation_id=conversation_id,
                limit=self.context_policy.recent_message_limit,
                include_internal_notes=self.context_policy.include_internal_notes,
            )
            or []
        )

        encoded_conversation = jsonable_encoder(conversation)
        encoded_conversation.pop("messages", None)

        return {
            "conversation": encoded_conversation,
            "recent_messages": jsonable_encoder(recent_messages),
            "customer": jsonable_encoder(getattr(conversation, "customer", None)),
            "ticket": jsonable_encoder(ticket),
            "tags": jsonable_encoder(tags),
            "insights": encoded_insights,
            "latest_insight": encoded_insights[0] if encoded_insights else None,
            "suggested_actions": jsonable_encoder(suggested_actions),
            "workflow_executions": jsonable_encoder(workflow_executions),
            "timeline": jsonable_encoder(timeline),
            "quality_reviews": jsonable_encoder(quality_reviews),
            "assignments": jsonable_encoder(assignments),
            "sla": {
                "violations": jsonable_encoder(sla_violations),
                "open": [
                    item
                    for item in jsonable_encoder(sla_violations)
                    if item.get("status") == "open"
                ],
                "breached": [
                    item
                    for item in jsonable_encoder(sla_violations)
                    if item.get("breached_at") is not None
                ],
            },
        }

    async def _list_assignments(self, *, user_id: UUID, ticket_id: UUID):
        result = await self.db.execute(
            select(TicketAssignment)
            .where(
                TicketAssignment.user_id == user_id,
                TicketAssignment.ticket_id == ticket_id,
            )
            .order_by(TicketAssignment.created_at.desc())
        )
        return result.scalars().all()

    async def _list_sla_violations(self, *, user_id: UUID, ticket_id: UUID):
        result = await self.db.execute(
            select(SLAViolation)
            .where(
                SLAViolation.user_id == user_id,
                SLAViolation.ticket_id == ticket_id,
            )
            .order_by(SLAViolation.due_at.asc())
        )
        return result.scalars().all()

    async def _list_quality_reviews(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
    ):
        result = await self.db.execute(
            select(CustomerServiceQualityReview)
            .where(
                CustomerServiceQualityReview.user_id == user_id,
                CustomerServiceQualityReview.conversation_id == conversation_id,
            )
            .order_by(CustomerServiceQualityReview.created_at.desc())
        )
        return result.scalars().all()
