from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    SLAPolicy,
    SLATargetType,
    SLAViolation,
    SLAViolationStatus,
    TicketPriority,
)


class SLARepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_policy(self, *, user_id, payload):
        policy = SLAPolicy(
            user_id=user_id,
            name=payload.name,
            priority=TicketPriority(payload.priority),
            first_response_minutes=payload.first_response_minutes,
            resolution_minutes=payload.resolution_minutes,
            business_hours=payload.business_hours,
            calendar_id=payload.calendar_id,
            is_active=payload.is_active,
        )

        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def list_policies(self, *, user_id):
        result = await self.db.execute(
            select(SLAPolicy)
            .where(SLAPolicy.user_id == user_id)
            .order_by(SLAPolicy.priority.asc(), SLAPolicy.created_at.desc())
        )
        return result.scalars().all()

    async def get_active_policy_for_priority(self, *, user_id, priority):
        result = await self.db.execute(
            select(SLAPolicy)
            .where(
                SLAPolicy.user_id == user_id,
                SLAPolicy.priority == priority,
                SLAPolicy.is_active.is_(True),
            )
            .order_by(SLAPolicy.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_violation_target(
        self,
        *,
        user_id,
        ticket_id,
        policy_id,
        target_type: SLATargetType,
        due_at,
    ):
        existing = await self.db.execute(
            select(SLAViolation).where(
                SLAViolation.user_id == user_id,
                SLAViolation.ticket_id == ticket_id,
                SLAViolation.target_type == target_type,
            )
        )
        target = existing.scalar_one_or_none()

        if target is not None:
            return target

        target = SLAViolation(
            user_id=user_id,
            ticket_id=ticket_id,
            policy_id=policy_id,
            target_type=target_type,
            due_at=due_at,
            status=SLAViolationStatus.OPEN,
        )

        self.db.add(target)
        await self.db.flush()
        return target

    async def list_violations(self, *, user_id, status: str | None = None):
        stmt = select(SLAViolation).where(SLAViolation.user_id == user_id)

        if status:
            stmt = stmt.where(SLAViolation.status == SLAViolationStatus(status))

        stmt = stmt.order_by(SLAViolation.due_at.asc())

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_open_due_targets(
        self,
        *,
        user_id,
        now: datetime | None = None,
    ):
        now = now or datetime.now(timezone.utc)

        result = await self.db.execute(
            select(SLAViolation)
            .where(
                SLAViolation.user_id == user_id,
                SLAViolation.status == SLAViolationStatus.OPEN,
                SLAViolation.due_at <= now,
                SLAViolation.breached_at.is_(None),
            )
            .order_by(SLAViolation.due_at.asc())
        )
        return result.scalars().all()

    async def list_open_targets(self, *, user_id):
        result = await self.db.execute(
            select(SLAViolation)
            .where(
                SLAViolation.user_id == user_id,
                SLAViolation.status == SLAViolationStatus.OPEN,
                SLAViolation.breached_at.is_(None),
            )
            .order_by(SLAViolation.due_at.asc())
        )
        return result.scalars().all()

    async def mark_breached(self, target, *, now: datetime | None = None):
        target.breached_at = now or datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(target)
        return target

    async def resolve_targets(self, *, ticket_id, target_type=None):
        stmt = select(SLAViolation).where(
            SLAViolation.ticket_id == ticket_id,
            SLAViolation.status == SLAViolationStatus.OPEN,
        )
        if target_type is not None:
            stmt = stmt.where(SLAViolation.target_type == target_type)
        result = await self.db.execute(stmt)
        targets = result.scalars().all()
        for target in targets:
            target.status = SLAViolationStatus.RESOLVED
        await self.db.commit()
        for target in targets:
            await self.db.refresh(target)
        return targets
