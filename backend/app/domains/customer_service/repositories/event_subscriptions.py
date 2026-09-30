from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    CustomerServiceEventSubscription,
    CustomerServiceWorkflowTemplate,
)


class CustomerServiceEventSubscriptionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        user_id: UUID,
        name: str,
        event_type: str,
        channel: str | None = None,
        workflow_template_id: UUID | None = None,
        workflow_json: dict | None = None,
        filters: dict | None = None,
        is_active: bool = True,
        meta: dict | None = None,
    ) -> CustomerServiceEventSubscription:
        subscription = CustomerServiceEventSubscription(
            user_id=user_id,
            name=name,
            event_type=event_type,
            channel=channel,
            workflow_template_id=workflow_template_id,
            workflow_json=workflow_json,
            filters=filters or {},
            is_active=is_active,
            meta=meta or {},
        )
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        limit: int = 100,
    ) -> list[CustomerServiceEventSubscription]:
        result = await self.db.execute(
            select(CustomerServiceEventSubscription)
            .where(CustomerServiceEventSubscription.user_id == user_id)
            .order_by(CustomerServiceEventSubscription.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_active_for_event(
        self,
        *,
        user_id: UUID,
        event_type: str,
        channel: str | None = None,
    ) -> list[CustomerServiceEventSubscription]:
        stmt = select(CustomerServiceEventSubscription).where(
            CustomerServiceEventSubscription.user_id == user_id,
            CustomerServiceEventSubscription.event_type == event_type,
            CustomerServiceEventSubscription.is_active.is_(True),
        )

        if channel:
            stmt = stmt.where(
                (CustomerServiceEventSubscription.channel.is_(None))
                | (CustomerServiceEventSubscription.channel == channel)
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(
        self,
        *,
        user_id: UUID,
        subscription_id: UUID,
    ) -> CustomerServiceEventSubscription | None:
        result = await self.db.execute(
            select(CustomerServiceEventSubscription).where(
                CustomerServiceEventSubscription.user_id == user_id,
                CustomerServiceEventSubscription.id == subscription_id,
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        *,
        subscription: CustomerServiceEventSubscription,
        values: dict,
    ) -> CustomerServiceEventSubscription:
        for key, value in values.items():
            setattr(subscription, key, value)

        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def delete(
        self,
        *,
        subscription: CustomerServiceEventSubscription,
    ) -> None:
        await self.db.delete(subscription)
        await self.db.commit()

    async def get_template(
        self,
        *,
        user_id: UUID,
        template_id: UUID,
    ) -> CustomerServiceWorkflowTemplate | None:
        result = await self.db.execute(
            select(CustomerServiceWorkflowTemplate).where(
                CustomerServiceWorkflowTemplate.id == template_id,
                CustomerServiceWorkflowTemplate.status == "published",
                (CustomerServiceWorkflowTemplate.scope == "system")
                | (CustomerServiceWorkflowTemplate.user_id == user_id),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        *,
        user_id,
        event_type,
        name,
    ):

        result = await self.db.execute(
            select(CustomerServiceEventSubscription).where(
                CustomerServiceEventSubscription.user_id == user_id,
                CustomerServiceEventSubscription.event_type == event_type,
                CustomerServiceEventSubscription.name == name,
            )
        )

        return result.scalar_one_or_none()
