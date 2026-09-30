from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.customer_service.repositories.analytics import AnalyticsRepository


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.repo = AnalyticsRepository(db)

    async def get_summary(self, user_id):
        return {
            "total_customers": await self.repo.count_customers(user_id),
            "total_conversations": await self.repo.count_conversations(user_id),
            "open_tickets": await self.repo.count_tickets_by_status(user_id, "open"),
            "pending_tickets": await self.repo.count_tickets_by_status(
                user_id, "pending"
            ),
            "closed_tickets": await self.repo.count_tickets_by_status(
                user_id, "closed"
            ),
            "urgent_tickets": await self.repo.count_tickets_by_priority(
                user_id, "urgent"
            ),
            "open_sla_breaches": await self.repo.open_sla_breaches(user_id),
        }

    async def workload(self, user_id):
        return await self.repo.workload_by_assignee(user_id)

    async def workload_report(self, user_id):
        return {
            "queues": await self.repo.queue_workload(user_id),
            "teams": await self.repo.team_workload(user_id),
            "agents": await self.repo.workload_by_assignee(user_id),
        }
