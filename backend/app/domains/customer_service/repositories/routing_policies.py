from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import CustomerServiceRoutingPolicy


class CustomerServiceRoutingPolicyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        user_id: UUID,
        name: str,
        channel: str | None,
        intent: str | None,
        priority: str | None,
        strategy: str,
        candidate_assignee_ids: list,
        candidate_team_ids: list | None = None,
        candidate_queue_ids: list | None = None,
        priority_rank: int = 100,
        is_fallback: bool = False,
        is_active: bool = True,
        filters: dict | None = None,
        meta: dict | None = None,
    ) -> CustomerServiceRoutingPolicy:
        policy = CustomerServiceRoutingPolicy(
            user_id=user_id,
            name=name,
            channel=channel,
            intent=intent,
            priority=priority,
            strategy=strategy,
            candidate_assignee_ids=[str(item) for item in candidate_assignee_ids],
            candidate_team_ids=[str(item) for item in (candidate_team_ids or [])],
            candidate_queue_ids=[str(item) for item in (candidate_queue_ids or [])],
            priority_rank=priority_rank,
            is_fallback=is_fallback,
            is_active=is_active,
            filters=filters or {},
            meta=meta or {},
        )
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        active_only: bool | None = None,
        limit: int = 100,
    ) -> list[CustomerServiceRoutingPolicy]:
        stmt = select(CustomerServiceRoutingPolicy).where(
            CustomerServiceRoutingPolicy.user_id == user_id,
        )

        if active_only is not None:
            stmt = stmt.where(CustomerServiceRoutingPolicy.is_active.is_(active_only))

        stmt = stmt.order_by(
            CustomerServiceRoutingPolicy.created_at.desc(),
        ).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(
        self,
        *,
        user_id: UUID,
        policy_id: UUID,
    ) -> CustomerServiceRoutingPolicy | None:
        result = await self.db.execute(
            select(CustomerServiceRoutingPolicy).where(
                CustomerServiceRoutingPolicy.user_id == user_id,
                CustomerServiceRoutingPolicy.id == policy_id,
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        *,
        policy: CustomerServiceRoutingPolicy,
        values: dict,
    ) -> CustomerServiceRoutingPolicy:
        if (
            "candidate_assignee_ids" in values
            and values["candidate_assignee_ids"] is not None
        ):
            values["candidate_assignee_ids"] = [
                str(item) for item in values["candidate_assignee_ids"]
            ]

        if "candidate_team_ids" in values and values["candidate_team_ids"] is not None:
            values["candidate_team_ids"] = [
                str(item) for item in values["candidate_team_ids"]
            ]

        if (
            "candidate_queue_ids" in values
            and values["candidate_queue_ids"] is not None
        ):
            values["candidate_queue_ids"] = [
                str(item) for item in values["candidate_queue_ids"]
            ]

        for key, value in values.items():
            setattr(policy, key, value)

        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def delete(
        self,
        *,
        policy: CustomerServiceRoutingPolicy,
    ) -> None:
        await self.db.delete(policy)
        await self.db.commit()

    async def list_matching(
        self,
        *,
        user_id: UUID,
        channel: str | None = None,
        intent: str | None = None,
        priority: str | None = None,
    ) -> list[CustomerServiceRoutingPolicy]:
        stmt = select(CustomerServiceRoutingPolicy).where(
            CustomerServiceRoutingPolicy.user_id == user_id,
            CustomerServiceRoutingPolicy.is_active.is_(True),
        )

        if channel is not None:
            stmt = stmt.where(
                (CustomerServiceRoutingPolicy.channel.is_(None))
                | (CustomerServiceRoutingPolicy.channel == channel)
            )

        if intent is not None:
            stmt = stmt.where(
                (CustomerServiceRoutingPolicy.intent.is_(None))
                | (CustomerServiceRoutingPolicy.intent == intent)
            )

        if priority is not None:
            stmt = stmt.where(
                (CustomerServiceRoutingPolicy.priority.is_(None))
                | (CustomerServiceRoutingPolicy.priority == priority)
            )

        result = await self.db.execute(
            stmt.order_by(
                CustomerServiceRoutingPolicy.is_fallback.asc(),
                CustomerServiceRoutingPolicy.priority_rank.asc(),
                CustomerServiceRoutingPolicy.created_at.desc(),
            )
        )
        return list(result.scalars().all())
