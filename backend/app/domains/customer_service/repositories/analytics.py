from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    Customer,
    Conversation,
    Ticket,
    SLAViolation,
    SLAViolationStatus,
    CustomerServiceQueue,
    CustomerServiceTeam,
    CustomerServiceTeamMember,
    CustomerServiceAgent,
)


class AnalyticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def count_customers(self, user_id) -> int:
        result = await self.db.execute(
            select(func.count(Customer.id)).where(Customer.user_id == user_id)
        )
        return int(result.scalar() or 0)

    async def count_conversations(self, user_id) -> int:
        result = await self.db.execute(
            select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
        )
        return int(result.scalar() or 0)

    async def count_tickets_by_status(self, user_id, status: str) -> int:
        result = await self.db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.user_id == user_id, Ticket.status == status
            )
        )
        return int(result.scalar() or 0)

    async def count_tickets_by_priority(self, user_id, priority: str) -> int:
        result = await self.db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.user_id == user_id, Ticket.priority == priority
            )
        )
        return int(result.scalar() or 0)

    async def workload_by_assignee(self, user_id):
        result = await self.db.execute(
            select(Ticket.assigned_to, func.count(Ticket.id))
            .where(
                Ticket.user_id == user_id,
                Ticket.assigned_to.is_not(None),
                Ticket.status.in_(["open", "pending"]),
            )
            .group_by(Ticket.assigned_to)
            .order_by(func.count(Ticket.id).desc())
        )
        return [
            {"assigned_to": row[0], "open_or_pending_tickets": int(row[1])}
            for row in result.all()
        ]

    async def open_sla_breaches(self, user_id) -> int:
        result = await self.db.execute(
            select(func.count(SLAViolation.id)).where(
                SLAViolation.user_id == user_id,
                SLAViolation.status == SLAViolationStatus.OPEN,
                SLAViolation.breached_at.is_not(None),
            )
        )
        return int(result.scalar() or 0)

    async def queue_workload(self, user_id):
        result = await self.db.execute(
            select(
                CustomerServiceQueue.id,
                CustomerServiceQueue.name,
                CustomerServiceQueue.team_id,
                CustomerServiceQueue.channel,
                CustomerServiceQueue.intent,
                CustomerServiceQueue.priority,
                func.count(Ticket.id),
            )
            .outerjoin(
                Conversation,
                (Conversation.user_id == CustomerServiceQueue.user_id)
                & (
                    (CustomerServiceQueue.channel.is_(None))
                    | (Conversation.channel == CustomerServiceQueue.channel)
                ),
            )
            .outerjoin(
                Ticket,
                (Ticket.user_id == CustomerServiceQueue.user_id)
                & (Ticket.conversation_id == Conversation.id)
                & (Ticket.status.in_(["open", "pending"]))
                & (
                    (CustomerServiceQueue.priority.is_(None))
                    | (cast(Ticket.priority, String) == CustomerServiceQueue.priority)
                ),
            )
            .where(
                CustomerServiceQueue.user_id == user_id,
                CustomerServiceQueue.is_active.is_(True),
            )
            .group_by(
                CustomerServiceQueue.id,
                CustomerServiceQueue.name,
                CustomerServiceQueue.team_id,
                CustomerServiceQueue.channel,
                CustomerServiceQueue.intent,
                CustomerServiceQueue.priority,
                CustomerServiceQueue.priority_rank,
            )
            .order_by(
                CustomerServiceQueue.priority_rank.asc(),
                CustomerServiceQueue.name.asc(),
            )
        )
        return [
            {
                "queue_id": row[0],
                "queue_name": row[1],
                "team_id": row[2],
                "channel": row[3],
                "intent": row[4],
                "priority": row[5],
                "open_or_pending_tickets": int(row[6] or 0),
            }
            for row in result.all()
        ]

    async def team_workload(self, user_id):
        member_counts = (
            select(
                CustomerServiceTeamMember.team_id.label("team_id"),
                func.count(CustomerServiceTeamMember.id).label("member_count"),
            )
            .where(CustomerServiceTeamMember.user_id == user_id)
            .group_by(CustomerServiceTeamMember.team_id)
            .subquery()
        )

        result = await self.db.execute(
            select(
                CustomerServiceTeam.id,
                CustomerServiceTeam.name,
                func.count(Ticket.id),
                func.coalesce(member_counts.c.member_count, 0),
            )
            .outerjoin(
                CustomerServiceTeamMember,
                CustomerServiceTeamMember.team_id == CustomerServiceTeam.id,
            )
            .outerjoin(
                CustomerServiceAgent,
                CustomerServiceAgent.id == CustomerServiceTeamMember.agent_id,
            )
            .outerjoin(
                Ticket,
                (Ticket.user_id == CustomerServiceTeam.user_id)
                & (Ticket.status.in_(["open", "pending"]))
                & (
                    Ticket.assigned_to
                    == cast(CustomerServiceAgent.agent_user_id, String)
                ),
            )
            .outerjoin(member_counts, member_counts.c.team_id == CustomerServiceTeam.id)
            .where(
                CustomerServiceTeam.user_id == user_id,
                CustomerServiceTeam.is_active.is_(True),
            )
            .group_by(
                CustomerServiceTeam.id,
                CustomerServiceTeam.name,
                member_counts.c.member_count,
            )
            .order_by(func.count(Ticket.id).desc(), CustomerServiceTeam.name.asc())
        )
        return [
            {
                "team_id": row[0],
                "team_name": row[1],
                "open_or_pending_tickets": int(row[2] or 0),
                "member_count": int(row[3] or 0),
            }
            for row in result.all()
        ]
