from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PlatformEvent


class PlatformEventStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def append(
        self,
        *,
        event_type: str,
        source: str,
        payload: dict,
        meta: dict | None = None,
        user_id=None,
        status: str = "published",
        commit: bool = True,
    ) -> PlatformEvent:
        event = PlatformEvent(
            user_id=user_id,
            event_type=event_type,
            source=source,
            payload=payload or {},
            meta=meta or {},
            status=status,
        )

        self.db.add(event)

        if commit:
            await self.db.commit()
            await self.db.refresh(event)
        else:
            await self.db.flush()

        return event

    async def get(
        self,
        event_id: UUID,
    ) -> PlatformEvent | None:
        result = await self.db.execute(
            select(PlatformEvent).where(
                PlatformEvent.id == event_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        *,
        user_id,
        limit: int = 100,
    ):
        result = await self.db.execute(
            select(PlatformEvent)
            .where(
                PlatformEvent.user_id
                == user_id
            )
            .order_by(
                PlatformEvent.created_at.desc()
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_type(
        self,
        *,
        event_type: str,
        limit: int = 100,
    ):
        result = await self.db.execute(
            select(PlatformEvent)
            .where(
                PlatformEvent.event_type
                == event_type
            )
            .order_by(
                PlatformEvent.created_at.desc()
            )
            .limit(limit)
        )
        return list(result.scalars().all())
