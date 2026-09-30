from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.objectives.learning.aggregation import (
    ObjectiveLearningAggregation,
    ObjectiveLearningAggregationPolicy,
    ObjectiveLearningAggregator,
    objective_learning_aggregation_key,
)
from app.runtime.objectives.learning.repository import (
    ObjectiveLearningExperienceRepository,
)


class ObjectiveLearningSummaryService:
    """
    Read-only aggregation over immutable objective-learning experiences.

    Returned summaries are informational and advisory only. This service
    does not persist summaries, publish events, enqueue jobs, rank options,
    retrieve planner guidance, or authorize execution.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: (ObjectiveLearningExperienceRepository | None) = None,
        aggregation_policy: (ObjectiveLearningAggregationPolicy | None) = None,
    ) -> None:
        self.db = db
        self.repository = repository or ObjectiveLearningExperienceRepository(db)
        self.aggregator = ObjectiveLearningAggregator(policy=aggregation_policy)

    async def summarize(
        self,
        *,
        user_id: UUID | str,
        window_hours: int = 720,
        tenant_id: str | None = None,
        objective_namespace: str | None = None,
        objective_type: str | None = None,
        objective_version: int | None = None,
        schema_ref: str | None = None,
        profile_ref: str | None = None,
        profile_version: int | None = None,
        extractor_ref: str | None = None,
        extractor_version: int | None = None,
        now: datetime | None = None,
    ) -> list[ObjectiveLearningAggregation]:
        (
            _window_start,
            _window_end,
            rows,
        ) = await self.repository.list_for_aggregation(
            user_id=user_id,
            window_hours=window_hours,
            tenant_id=tenant_id,
            objective_namespace=(objective_namespace),
            objective_type=objective_type,
            objective_version=(objective_version),
            schema_ref=schema_ref,
            profile_ref=profile_ref,
            profile_version=profile_version,
            extractor_ref=extractor_ref,
            extractor_version=(extractor_version),
            now=now,
        )

        grouped: dict[
            str,
            list[Any],
        ] = defaultdict(list)

        for row in rows:
            key = objective_learning_aggregation_key(row)
            grouped[key].append(row)

        summaries = [
            self.aggregator.summarize(experiences=experiences)
            for experiences in grouped.values()
        ]

        return sorted(
            summaries,
            key=lambda summary: (
                summary.tenant_id or "",
                summary.objective_namespace,
                summary.objective_type,
                summary.objective_version,
                summary.schema_ref,
                summary.profile_ref,
                summary.profile_version,
                summary.extractor_ref,
                summary.extractor_version,
                summary.scope_fingerprint,
            ),
        )


__all__ = [
    "ObjectiveLearningSummaryService",
]
