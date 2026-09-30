from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import WorkflowWait
from app.workflow_operations.waits.service import WorkflowWaitService


class WorkflowWaitEventResolver:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = WorkflowWaitService(db)

    async def resolve_for_event(self, *, event, limit: int = 100):
        event_type = event.event_type
        event_payload = event.payload or {}

        result = await self.db.execute(
            select(WorkflowWait)
            .where(
                WorkflowWait.user_id == event.user_id,
                WorkflowWait.status == "waiting",
                WorkflowWait.wait_type == "event",
            )
            .order_by(WorkflowWait.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        )

        waits = list(result.scalars().all())
        resolved = []

        for wait in waits:
            wait_payload = wait.payload or {}

            if wait_payload.get("event_type") != event_type:
                continue

            if not self._matches(wait_payload.get("match") or {}, event_payload):
                continue

            result = await self.service.resolve(
                user_id=wait.user_id,
                wait_id=wait.id,
                resolution={
                    "event": {
                        "id": str(event.id),
                        "event_type": event.event_type,
                        "source": event.source,
                        "payload": event.payload,
                        "meta": event.meta,
                    }
                },
                resume=True,
            )

            resolved.append(result["wait"])

        return resolved

    def _matches(self, match: dict, payload: dict) -> bool:
        for key, expected in match.items():
            if payload.get(key) != expected:
                return False
        return True
