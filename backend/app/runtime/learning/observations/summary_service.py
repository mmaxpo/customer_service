from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.learning.observations.aggregation import (
    BusinessLearningAggregationPolicy,
    BusinessLearningAggregator,
    BusinessLearningSummary,
)
from app.runtime.learning.observations.repository import (
    BusinessLearningObservationRepository,
)


class BusinessLearningSummaryService:
    """
    Read-only aggregation over immutable business
    learning observations.

    Returned summaries are descriptive and advisory.
    This service does not mutate planning, workflow
    policy, routing, or runtime behavior.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: (
            BusinessLearningObservationRepository
            | None
        ) = None,
        policy: (
            BusinessLearningAggregationPolicy
            | None
        ) = None,
    ) -> None:
        self.db = db
        self.repository = (
            repository
            or BusinessLearningObservationRepository(
                db
            )
        )
        self.aggregator = (
            BusinessLearningAggregator(
                policy=policy
            )
        )

    async def summarize(
        self,
        *,
        user_id: UUID,
        window_hours: int = 720,
        tenant_id: str | None = None,
        objective_namespace: str | None = None,
        objective_type: str | None = None,
        decision: str | None = None,
        now: datetime | None = None,
    ) -> list[BusinessLearningSummary]:
        (
            window_start,
            window_end,
            rows,
        ) = await (
            self.repository.list_for_aggregation(
                user_id=user_id,
                window_hours=window_hours,
                tenant_id=tenant_id,
                objective_namespace=(
                    objective_namespace
                ),
                objective_type=objective_type,
                decision=decision,
                now=now,
            )
        )

        grouped: dict[
            tuple[
                str | None,
                str,
                str,
                str,
            ],
            list[Any],
        ] = defaultdict(list)

        for row in rows:
            key = (
                row.tenant_id,
                str(row.objective_namespace),
                str(row.objective_type),
                str(row.decision),
            )
            grouped[key].append(row)

        summaries = [
            self.aggregator.summarize(
                observations=observations,
                tenant_id=scope[0],
                objective_namespace=scope[1],
                objective_type=scope[2],
                decision=scope[3],
                window_start=window_start,
                window_end=window_end,
            )
            for scope, observations
            in grouped.items()
        ]

        return sorted(
            summaries,
            key=lambda summary: (
                summary.tenant_id or "",
                summary.objective_namespace,
                summary.objective_type,
                summary.decision,
            ),
        )


__all__ = [
    "BusinessLearningSummaryService",
]
