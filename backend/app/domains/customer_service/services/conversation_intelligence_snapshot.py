from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    Conversation,
    ConversationTag,
    SLAViolation,
    SLAViolationStatus,
    Ticket,
)
from app.domains.customer_service.services.conversation_intelligence import (
    ConversationIntelligenceService,
)
from app.domains.customer_service.services.customer_risk import CustomerRiskService


class ConversationIntelligenceSnapshotService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_snapshot(self, *, user_id: UUID, conversation_id: UUID) -> dict:
        conversation = await self._conversation(
            user_id=user_id, conversation_id=conversation_id
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        ticket = await self._ticket(user_id=user_id, conversation_id=conversation_id)
        tags = await self._tags(user_id=user_id, conversation_id=conversation_id)

        insight = await ConversationIntelligenceService(self.db).analyze(
            user_id=user_id,
            conversation_id=conversation_id,
            force_refresh=False,
        )

        risk = await CustomerRiskService(self.db).get_customer_risk(
            user_id=user_id,
            customer_id=conversation.customer_id,
        )

        sla_risk = False
        if ticket is not None:
            sla_risk = await self._sla_risk(user_id=user_id, ticket_id=ticket.id)

        intent = getattr(insight, "intent", None)
        urgency = getattr(insight, "urgency", None)
        sentiment = getattr(insight, "sentiment", None)

        return {
            "conversation_id": conversation.id,
            "intent": intent,
            "urgency": urgency,
            "sentiment": sentiment,
            "summary": getattr(insight, "summary", None),
            "sla_risk": sla_risk,
            "customer_risk_score": risk["risk_score"] if risk else None,
            "customer_risk_level": risk["risk_level"] if risk else None,
            "open_ticket": self._ticket_is_open(ticket),
            "ticket_priority": self._value(ticket.priority)
            if ticket is not None
            else None,
            "recommended_actions": self._recommended_actions(
                intent=intent,
                urgency=urgency,
                sentiment=sentiment,
                tags=tags,
                sla_risk=sla_risk,
                customer_risk_level=risk["risk_level"] if risk else None,
                ticket=ticket,
            ),
            "tags": sorted(tags),
            "metadata": {
                "customer_id": str(conversation.customer_id),
                "ticket_id": str(ticket.id) if ticket is not None else None,
                "insight_id": str(insight.id) if insight is not None else None,
            },
        }

    async def _conversation(self, *, user_id: UUID, conversation_id: UUID):
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.id == conversation_id,
            )
        )
        return result.scalar_one_or_none()

    async def _ticket(self, *, user_id: UUID, conversation_id: UUID):
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.user_id == user_id,
                Ticket.conversation_id == conversation_id,
            )
        )
        return result.scalar_one_or_none()

    async def _tags(self, *, user_id: UUID, conversation_id: UUID) -> set[str]:
        result = await self.db.execute(
            select(ConversationTag).where(
                ConversationTag.user_id == user_id,
                ConversationTag.conversation_id == conversation_id,
            )
        )
        return {tag.name for tag in result.scalars().all() if tag.name}

    async def _sla_risk(self, *, user_id: UUID, ticket_id: UUID) -> bool:
        now = datetime.now(timezone.utc)
        soon = now + timedelta(minutes=30)

        result = await self.db.execute(
            select(SLAViolation).where(
                SLAViolation.user_id == user_id,
                SLAViolation.ticket_id == ticket_id,
                SLAViolation.status == SLAViolationStatus.OPEN,
            )
        )

        for violation in result.scalars().all():
            if violation.breached_at is not None:
                return True
            if violation.due_at <= soon:
                return True

        return False

    def _recommended_actions(
        self,
        *,
        intent,
        urgency,
        sentiment,
        tags: set[str],
        sla_risk: bool,
        customer_risk_level,
        ticket,
    ) -> list[str]:
        actions = []

        if intent == "refund_request" or "refund" in tags:
            actions.append("review_refund_request")

        if intent in {"cancellation", "cancellation_request"}:
            actions.append("review_cancellation_request")

        if intent == "damaged_item" or "damaged_item" in tags:
            actions.append("open_damaged_item_case")

        if intent in {"shipping_delay", "tracking_request"}:
            actions.append("check_shipping_status")

        if urgency == "high" or sentiment == "negative":
            actions.append("respond_with_priority")

        if sla_risk:
            actions.append("protect_sla")

        if customer_risk_level == "high":
            actions.append("assign_human_agent")

        if ticket is not None and self._value(ticket.priority) in {"high", "urgent"}:
            actions.append("escalate_ticket")

        return list(dict.fromkeys(actions))

    def _ticket_is_open(self, ticket) -> bool:
        if ticket is None:
            return False
        return self._value(ticket.status) in {"open", "pending"}

    def _value(self, value) -> str:
        return getattr(value, "value", str(value))
