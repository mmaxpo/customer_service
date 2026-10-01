from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    Customer,
    Conversation,
    ConversationTag,
    Ticket,
    TicketPriority,
    SLAViolation,
)


class CustomerRiskService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _leaderboard_candidate_limit(self, limit: int) -> int:
        # Risk leaderboard is intentionally computed from a bounded candidate
        # set. Scoring every customer would run several queries per customer.
        #
        # Future production upgrade: persist risk snapshots and sort directly
        # from a risk_score column/materialized table.
        return min(max(limit * 20, 100), 1000)

    async def get_customer_risk(self, *, user_id, customer_id):
        customer = await self._customer(user_id, customer_id)
        if customer is None:
            return None

        score = 0
        signals: list[str] = []

        conversation_ids = await self._conversation_ids(
            user_id=user_id,
            customer_id=customer_id,
        )

        tickets = await self._tickets(
            user_id=user_id,
            conversation_ids=conversation_ids,
        )

        open_tickets = [
            t
            for t in tickets
            if getattr(t.status, "value", str(t.status)) in {"open", "pending"}
        ]

        if open_tickets:
            score += min(len(open_tickets) * 15, 30)
            signals.append(f"{len(open_tickets)} open tickets")

        if any(t.priority == TicketPriority.HIGH for t in tickets):
            score += 25
            signals.append("high priority ticket")

        breaches = await self._sla_breaches(
            user_id=user_id,
            ticket_ids=[t.id for t in tickets],
        )

        if breaches:
            score += min(len(breaches) * 20, 40)
            signals.append(f"{len(breaches)} sla breaches")

        tags = await self._tags(
            user_id=user_id,
            conversation_ids=conversation_ids,
        )

        if "refund" in tags:
            score += 15
            signals.append("refund request")

        if "damaged_item" in tags:
            score += 10
            signals.append("damaged item")

        if "chargeback" in tags:
            score += 30
            signals.append("chargeback risk")

        score = min(score, 100)

        if score >= 60:
            level = "high"
        elif score >= 30:
            level = "medium"
        else:
            level = "low"

        return {
            "customer_id": str(customer_id),
            "risk_score": score,
            "risk_level": level,
            "signals": signals,
        }

    async def leaderboard(self, *, user_id, limit: int = 25):
        candidate_limit = self._leaderboard_candidate_limit(limit)

        result = await self.db.execute(
            select(Customer)
            .where(Customer.user_id == user_id)
            .order_by(Customer.created_at.desc())
            .limit(candidate_limit)
        )

        customers = result.scalars().all()

        rows = []

        for customer in customers:
            risk = await self.get_customer_risk(
                user_id=user_id,
                customer_id=customer.id,
            )

            rows.append(
                {
                    "customer_id": str(customer.id),
                    "name": customer.name,
                    "risk_score": risk["risk_score"],
                    "risk_level": risk["risk_level"],
                }
            )

        rows.sort(
            key=lambda x: x["risk_score"],
            reverse=True,
        )

        return rows[:limit]

    async def _customer(self, user_id, customer_id):
        result = await self.db.execute(
            select(Customer).where(
                Customer.user_id == user_id,
                Customer.id == customer_id,
            )
        )
        return result.scalar_one_or_none()

    async def _conversation_ids(self, *, user_id, customer_id):
        result = await self.db.execute(
            select(Conversation.id).where(
                Conversation.user_id == user_id,
                Conversation.customer_id == customer_id,
            )
        )
        return list(result.scalars().all())

    async def _tickets(self, *, user_id, conversation_ids):
        if not conversation_ids:
            return []

        result = await self.db.execute(
            select(Ticket).where(
                Ticket.user_id == user_id,
                Ticket.conversation_id.in_(conversation_ids),
            )
        )
        return list(result.scalars().all())

    async def _sla_breaches(self, *, user_id, ticket_ids):
        if not ticket_ids:
            return []

        result = await self.db.execute(
            select(SLAViolation).where(
                SLAViolation.user_id == user_id,
                SLAViolation.ticket_id.in_(ticket_ids),
                SLAViolation.breached_at.is_not(None),
            )
        )
        return list(result.scalars().all())

    async def _tags(self, *, user_id, conversation_ids):
        if not conversation_ids:
            return set()

        result = await self.db.execute(
            select(ConversationTag).where(
                ConversationTag.user_id == user_id,
                ConversationTag.conversation_id.in_(conversation_ids),
            )
        )

        return {tag.name for tag in result.scalars().all()}
