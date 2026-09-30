from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import CustomerServiceAuditLog


class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        user_id,
        action: str,
        entity_type: str,
        entity_id=None,
        actor_id=None,
        message: str | None = None,
        meta: dict | None = None,
        commit: bool = True,
    ):
        log = CustomerServiceAuditLog(
            user_id=user_id,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            message=message,
            meta=meta,
        )
        self.db.add(log)
        if commit:
            await self.db.commit()
            await self.db.refresh(log)
        else:
            await self.db.flush()
        return log

    async def list(
        self,
        *,
        user_id,
        entity_type: str | None = None,
        entity_id=None,
        limit: int = 100,
    ):
        stmt = select(CustomerServiceAuditLog).where(
            CustomerServiceAuditLog.user_id == user_id
        )
        if entity_type:
            stmt = stmt.where(CustomerServiceAuditLog.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(CustomerServiceAuditLog.entity_id == entity_id)
        stmt = stmt.order_by(CustomerServiceAuditLog.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
