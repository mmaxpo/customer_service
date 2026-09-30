from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.learning.aggregation import (
    CapabilityLearningAggregationPolicy,
    CapabilityLearningAggregator,
)
from app.runtime.capabilities.execution.learning.repository import (
    CapabilityLearningObservationRepository,
)
from app.runtime.capabilities.execution.learning.trends import (
    CapabilityLearningTrendAnalyzer,
    CapabilityLearningTrendPolicy,
    CapabilityLearningTrendReport,
)


Scope = tuple[
    str,
    str | None,
    str | None,
    str | None,
    str | None,
]


class CapabilityLearningTrendService:
    """
    Compare adjacent, non-overlapping learning windows.

    Reports are read-only and advisory. This service does not mutate
    provider scoring, routing, traffic allocation, health, or policy.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: (
            CapabilityLearningObservationRepository
            | None
        ) = None,
        aggregation_policy: (
            CapabilityLearningAggregationPolicy
            | None
        ) = None,
        trend_policy: (
            CapabilityLearningTrendPolicy
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
                policy=aggregation_policy
            )
        )
        self.analyzer = (
            CapabilityLearningTrendAnalyzer(
                policy=trend_policy
            )
        )

    async def analyze(
        self,
        *,
        user_id: UUID,
        window_hours: int = 168,
        tenant_id: str | None = None,
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        action: str | None = None,
        now: datetime | None = None,
    ) -> list[CapabilityLearningTrendReport]:
        if window_hours < 1 or window_hours > 4380:
            raise ValueError(
                "window_hours must be between 1 and 4380"
            )

        recent_end = now or datetime.now(
            timezone.utc
        )

        if recent_end.tzinfo is None:
            recent_end = recent_end.replace(
                tzinfo=timezone.utc
            )

        recent_start = recent_end - timedelta(
            hours=window_hours
        )
        historical_start = (
            recent_start
            - timedelta(hours=window_hours)
        )

        (
            query_start,
            query_end,
            rows,
        ) = await self.repository.list_for_aggregation(
            user_id=user_id,
            window_hours=window_hours * 2,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
            action=action,
            now=recent_end,
        )

        if query_start != historical_start:
            historical_start = query_start

        if query_end != recent_end:
            recent_end = query_end
            recent_start = (
                recent_end
                - timedelta(hours=window_hours)
            )

        historical_groups: dict[
            Scope,
            list[Any],
        ] = defaultdict(list)

        recent_groups: dict[
            Scope,
            list[Any],
        ] = defaultdict(list)

        for row in rows:
            observed_at = _aware(
                row.observed_at
            )
            scope = _scope(row)

            if (
                historical_start
                <= observed_at
                < recent_start
            ):
                historical_groups[scope].append(row)
            elif (
                recent_start
                <= observed_at
                < recent_end
            ):
                recent_groups[scope].append(row)

        scopes = sorted(
            set(historical_groups)
            | set(recent_groups),
            key=_scope_sort_key,
        )

        reports: list[
            CapabilityLearningTrendReport
        ] = []

        for scope in scopes:
            historical = (
                self.aggregator.summarize(
                    observations=(
                        historical_groups.get(
                            scope,
                            [],
                        )
                    ),
                    capability_id=scope[0],
                    provider_id=scope[1],
                    provider_ref=scope[2],
                    tenant_id=scope[3],
                    action=scope[4],
                    window_start=(
                        historical_start
                    ),
                    window_end=recent_start,
                )
            )

            recent = self.aggregator.summarize(
                observations=(
                    recent_groups.get(
                        scope,
                        [],
                    )
                ),
                capability_id=scope[0],
                provider_id=scope[1],
                provider_ref=scope[2],
                tenant_id=scope[3],
                action=scope[4],
                window_start=recent_start,
                window_end=recent_end,
            )

            reports.append(
                self.analyzer.compare(
                    historical=historical,
                    recent=recent,
                )
            )

        return reports


def _scope(row: Any) -> Scope:
    return (
        str(row.capability_id),
        row.provider_id,
        row.provider_ref,
        row.tenant_id,
        row.action,
    )


def _scope_sort_key(
    scope: Scope,
) -> tuple[str, str, str, str, str]:
    return (
        scope[0],
        scope[1] or "",
        scope[2] or "",
        scope[3] or "",
        scope[4] or "",
    )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value


__all__ = [
    "CapabilityLearningTrendService",
]
