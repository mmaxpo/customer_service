from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    CapabilityPerformanceObservationRecord,
    PlatformEvent,
)


class CapabilityHealthEvaluationScope(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    user_id: UUID
    tenant_id: str | None = None
    capability_id: str
    provider_id: str
    provider_ref: str | None = None


class CapabilityHealthScopeRepository:
    """
    Discover authenticated capability/provider scopes with evidence.

    PlatformEvent.user_id is the authoritative ownership boundary. The
    observation's copied user_id remains diagnostic projection data only.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def discover_for_window(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[CapabilityHealthEvaluationScope]:
        observation = (
            CapabilityPerformanceObservationRecord
        )
        capability_expression = func.coalesce(
            observation.resolved_capability_id,
            observation.requested_capability_id,
        )

        stmt = (
            select(
                PlatformEvent.user_id.label("user_id"),
                observation.tenant_id.label(
                    "tenant_id"
                ),
                capability_expression.label(
                    "capability_id"
                ),
                observation.provider_id.label(
                    "provider_id"
                ),
                observation.provider_ref.label(
                    "provider_ref"
                ),
            )
            .join(
                PlatformEvent,
                PlatformEvent.id
                == observation.source_event_id,
            )
            .where(
                PlatformEvent.user_id.is_not(None),
                observation.provider_id.is_not(None),
                observation.observed_at >= window_start,
                observation.observed_at < window_end,
            )
            .group_by(
                PlatformEvent.user_id,
                observation.tenant_id,
                capability_expression,
                observation.provider_id,
                observation.provider_ref,
            )
            .order_by(
                PlatformEvent.user_id,
                observation.tenant_id,
                capability_expression,
                observation.provider_id,
                observation.provider_ref,
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)

        return [
            CapabilityHealthEvaluationScope(
                user_id=row.user_id,
                tenant_id=row.tenant_id,
                capability_id=row.capability_id,
                provider_id=row.provider_id,
                provider_ref=row.provider_ref,
            )
            for row in result
        ]


__all__ = [
    "CapabilityHealthEvaluationScope",
    "CapabilityHealthScopeRepository",
]
