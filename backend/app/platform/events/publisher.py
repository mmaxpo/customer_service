from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.events.event_bus import (
    PlatformEventBus,
)


class PlatformEventPublisher:
    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    async def publish(
        self,
        *,
        event_type: str,
        source: str = "platform",
        payload: dict | None = None,
        meta: dict | None = None,
        user_id=None,
        dispatch: bool = True,
        commit: bool = True,
    ):
        return await PlatformEventBus(
            self.db
        ).publish(
            event_type=event_type,
            source=source,
            payload=payload or {},
            meta=meta or {},
            user_id=user_id,
            dispatch=dispatch,
            commit=commit,
        )
