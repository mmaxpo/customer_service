from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.learning.observations.aggregation import (
    BusinessLearningAggregationPolicy,
    BusinessLearningAggregator,
)
from app.runtime.learning.observations.repository import (
    BusinessLearningObservationRepository,
)
from app.runtime.learning.observations.trends import (
    BusinessLearningTrendAnalyzer,
    BusinessLearningTrendPolicy,
    BusinessLearningTrendReport,
)


Scope = tuple[
    str | None,
    str,
    str,
    str,
]


class BusinessLearningTrendService:
    """
    Compare adjacent, equal-duration business-learning
    windows.

    Reports are read-only and do not mutate planning,
    workflows, routing, or runtime policy.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: (
            BusinessLearningObservationRepository
            | None
        ) = None,
        aggregation_policy: (
            BusinessLearningAggregationPolicy
            | None
        ) = None,
        trend_policy: (
            BusinessLearningTrendPolicy
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
                policy=aggregation_policy
            )
        )
        self.analyzer = (
            BusinessLearningTrendAnalyzer(
                policy=trend_policy
            )
        )

    async def analyze(
        self,
        *,
        user_id: UUID,
        window_hours: int = 168,
        tenant_id: str | None = None,
        objective_namespace: str | None = None,
        objective_type: str | None = None,
        decision: str | None = None,
        now: datetime | None = None,
    ) -> list[BusinessLearningTrendReport]:
        if window_hours < 1 or window_hours > 4380:
            raise ValueError(
                "window_hours must be between "
                "1 and 4380"
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
        ) = await (
            self.repository.list_for_aggregation(
                user_id=user_id,
                window_hours=window_hours * 2,
                tenant_id=tenant_id,
                objective_namespace=(
                    objective_namespace
                ),
                objective_type=objective_type,
                decision=decision,
                now=recent_end,
            )
        )

        historical_start = query_start
        recent_end = query_end
        recent_start = recent_end - timedelta(
            hours=window_hours
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
                historical_groups[scope].append(
                    row
                )
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
            BusinessLearningTrendReport
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
                    tenant_id=scope[0],
                    objective_namespace=scope[1],
                    objective_type=scope[2],
                    decision=scope[3],
                    window_start=historical_start,
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
                tenant_id=scope[0],
                objective_namespace=scope[1],
                objective_type=scope[2],
                decision=scope[3],
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


def _scope(
    row: Any,
) -> Scope:
    return (
        row.tenant_id,
        str(row.objective_namespace),
        str(row.objective_type),
        str(row.decision),
    )


def _scope_sort_key(
    scope: Scope,
) -> tuple[str, str, str, str]:
    return (
        scope[0] or "",
        scope[1],
        scope[2],
        scope[3],
    )


def _aware(
    value: datetime,
) -> datetime:
    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value


__all__ = [
    "BusinessLearningTrendService",
]
