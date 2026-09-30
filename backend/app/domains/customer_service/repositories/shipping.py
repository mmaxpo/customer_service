from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    CustomerServiceShippingTrackingCache,
)


class ShippingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_cached_tracking(
        self,
        *,
        user_id,
        provider: str,
        tracking_number: str,
    ):
        result = await self.db.execute(
            select(CustomerServiceShippingTrackingCache)
            .where(
                CustomerServiceShippingTrackingCache.user_id == user_id,
                CustomerServiceShippingTrackingCache.provider == provider,
                CustomerServiceShippingTrackingCache.tracking_number == tracking_number,
            )
            .order_by(CustomerServiceShippingTrackingCache.updated_at.desc())
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def cache_tracking(
        self,
        *,
        user_id,
        provider: str,
        tracking_number: str,
        status: str | None,
        payload: dict,
    ):
        obj = CustomerServiceShippingTrackingCache(
            user_id=user_id,
            provider=provider,
            tracking_number=tracking_number,
            status=status,
            payload=payload,
        )

        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj
