from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.composition import (
    build_default_event_registry,
)
from app.platform.events.event_store import (
    PlatformEventStore,
)
from app.platform.events.registry import (
    EventContext,
    EventHandlerRegistry,
)


class PlatformEventBus:
    def __init__(
        self,
        db: AsyncSession,
        *,
        registry: EventHandlerRegistry | None = None,
    ):
        self.db = db
        self.registry = (
            registry if registry is not None else build_default_event_registry()
        )
        self.store = PlatformEventStore(db)

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
        event = await self.store.append(
            event_type=event_type,
            source=source,
            payload=payload or {},
            meta=meta or {},
            user_id=user_id,
            status="published",
            commit=commit,
        )

        handler_results = []

        if dispatch:
            ctx = EventContext(
                db=self.db,
                event=event,
            )

            for handler in self.registry.handlers_for(event.event_type):
                result = await handler(
                    event,
                    ctx,
                )
                handler_results.append(result or {})

        return {
            "event": event,
            "handler_results": handler_results,
        }
