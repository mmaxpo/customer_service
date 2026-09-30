from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import WebhookDelivery, WebhookEndpoint


class WebhookRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_endpoint(
        self, *, user_id, name, source, workflow_id, secret, config
    ):
        endpoint = WebhookEndpoint(
            user_id=user_id,
            name=name,
            source=source,
            workflow_id=workflow_id,
            secret=secret,
            config=config or {},
            status="active",
        )
        self.db.add(endpoint)
        await self.db.commit()
        await self.db.refresh(endpoint)
        return endpoint

    async def get_endpoint(self, *, endpoint_id: UUID):
        result = await self.db.execute(
            select(WebhookEndpoint).where(WebhookEndpoint.id == endpoint_id)
        )
        return result.scalar_one_or_none()

    async def list_endpoints(self, *, user_id):
        result = await self.db.execute(
            select(WebhookEndpoint)
            .where(WebhookEndpoint.user_id == user_id)
            .order_by(WebhookEndpoint.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_delivery(
        self,
        *,
        endpoint,
        event_type: str,
        payload: dict,
        headers: dict,
        job_id=None,
        status: str = "accepted",
        error_message: str | None = None,
    ):
        delivery = WebhookDelivery(
            endpoint_id=endpoint.id,
            user_id=endpoint.user_id,
            source=endpoint.source,
            event_type=event_type,
            payload=payload or {},
            headers=headers or {},
            job_id=job_id,
            status=status,
            error_message=error_message,
        )
        self.db.add(delivery)
        await self.db.commit()
        await self.db.refresh(delivery)
        return delivery
