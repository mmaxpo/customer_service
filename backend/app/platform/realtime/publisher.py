from __future__ import annotations

from uuid import UUID

from app.platform.realtime.hub import realtime_hub
from app.platform.realtime.schemas import RealtimeEvent


class RealtimePublisher:
    async def publish(
        self,
        *,
        user_id: UUID,
        type: str,
        scope: str,
        entity_type: str | None = None,
        entity_id: UUID | str | None = None,
        payload: dict | None = None,
    ) -> RealtimeEvent:
        event = RealtimeEvent(
            user_id=user_id,
            type=type,
            scope=scope,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )

        await realtime_hub.publish(event)
        return event


realtime_publisher = RealtimePublisher()
