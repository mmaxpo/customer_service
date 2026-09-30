from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.learning.aggregation import (
    CapabilityLearningAggregationPolicy,
    CapabilityLearningAggregator,
    CapabilityLearningSummary,
)
from app.runtime.capabilities.execution.learning.repository import (
    CapabilityLearningObservationRepository,
)


class CapabilityLearningSummaryService:
    """
    Read-only aggregation over immutable learning observations.

    Returned summaries are advisory. This service does not mutate provider
    selection, health, allocation, or runtime policy.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: (
            CapabilityLearningObservationRepository
            | None
        ) = None,
        policy: (
            CapabilityLearningAggregationPolicy
            | None
        ) = None,
    ) -> None:
        self.db = db
        self.repository = (
            repository
            or CapabilityLearningObservationRepository(
                db
            )
        )
        self.aggregator = (
            CapabilityLearningAggregator(
                policy=policy
            )
        )

    async def summarize(
        self,
        *,
        user_id: UUID,
        window_hours: int = 720,
        tenant_id: str | None = None,
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        action: str | None = None,
        now: datetime | None = None,
    ) -> list[CapabilityLearningSummary]:
        (
            window_start,
            window_end,
            rows,
        ) = await self.repository.list_for_aggregation(
            user_id=user_id,
            window_hours=window_hours,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
            action=action,
            now=now,
        )

        grouped: dict[
            tuple[
                str,
                str | None,
                str | None,
                str | None,
                str | None,
            ],
            list[Any],
        ] = defaultdict(list)

        for row in rows:
            key = (
                str(row.capability_id),
                row.provider_id,
                row.provider_ref,
                row.tenant_id,
                row.action,
            )
            grouped[key].append(row)

        summaries = [
            self.aggregator.summarize(
                observations=observations,
                capability_id=scope[0],
                provider_id=scope[1],
                provider_ref=scope[2],
                tenant_id=scope[3],
                action=scope[4],
                window_start=window_start,
                window_end=window_end,
            )
            for scope, observations in grouped.items()
        ]

        return sorted(
            summaries,
            key=lambda summary: (
                summary.capability_id,
                summary.provider_id or "",
                summary.provider_ref or "",
                summary.tenant_id or "",
                summary.action or "",
            ),
        )


__all__ = [
    "CapabilityLearningSummaryService",
]
