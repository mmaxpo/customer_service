from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.customer_service.repositories.audit_logs import AuditLogRepository


class AuditLogService:
    def __init__(self, db: AsyncSession):
        self.repo = AuditLogRepository(db)

    async def list_logs(
        self,
        *,
        user_id,
        entity_type: str | None = None,
        entity_id=None,
        limit: int = 100,
    ):
        return await self.repo.list(
            user_id=user_id, entity_type=entity_type, entity_id=entity_id, limit=limit
        )
