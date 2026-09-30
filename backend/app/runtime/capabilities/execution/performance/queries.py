from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import (
    and_,
    case,
    exists,
    func,
    select,
)
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    CapabilityPerformanceObservationRecord,
    PlatformEvent,
)


def _normalize_user_id(value: Any) -> UUID:
    """
    Normalize authenticated ownership IDs for PlatformEvent.user_id.

    Callers may provide either a UUID instance or a UUID string.
    """

    if isinstance(value, UUID):
        return value

    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(
            "user_id must be a valid UUID"
        ) from exc


class CapabilityPerformanceQueryRepository:
    """
    Read-only query repository for durable capability observations.

    Every public query requires user_id. Optional tenant filtering is always
    applied inside that authenticated ownership boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def summarize(
        self,
        *,
        user_id,
        window_hours: int = 24,
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        tenant_id: str | None = None,
        now: datetime | None = None,
    ) -> tuple[datetime, datetime, list[dict[str, Any]]]:
        normalized_user_id = _normalize_user_id(user_id)
        window_end = now or datetime.now(timezone.utc)

        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=timezone.utc)

        window_start = window_end - timedelta(
            hours=window_hours
        )

        observation = CapabilityPerformanceObservationRecord
        later_attempt = aliased(
            CapabilityPerformanceObservationRecord
        )

        capability_expression = func.coalesce(
            observation.resolved_capability_id,
            observation.requested_capability_id,
        )

        fallback_recovered = exists(
            select(1).where(
                later_attempt.source_event_id
                == observation.source_event_id,
                later_attempt.attempt_index
                > observation.attempt_index,
                later_attempt.succeeded.is_(True),
            )
        )

        filters = [
            PlatformEvent.user_id == normalized_user_id,
            observation.observed_at >= window_start,
            observation.observed_at < window_end,
        ]

        if capability_id is not None:
            filters.append(
                capability_expression == capability_id
            )

        if provider_id is not None:
            filters.append(
                observation.provider_id == provider_id
            )

        if provider_ref is not None:
            filters.append(
                observation.provider_ref == provider_ref
            )

        if tenant_id is not None:
            filters.append(
                observation.tenant_id == tenant_id
            )

        stmt = (
            select(
                capability_expression.label("capability_id"),
                observation.provider_id.label("provider_id"),
                observation.provider_ref.label("provider_ref"),
                observation.tenant_id.label("tenant_id"),
                func.count(observation.id).label("attempts"),
                func.sum(
                    case(
                        (
                            observation.succeeded.is_(True),
                            1,
                        ),
                        else_=0,
                    )
                ).label("successes"),
                func.sum(
                    case(
                        (
                            observation.succeeded.is_(False),
                            1,
                        ),
                        else_=0,
                    )
                ).label("failures"),
                func.sum(
                    case(
                        (
                            and_(
                                observation.succeeded.is_(False),
                                observation.failure_kind
                                == "timeout",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("timeouts"),
                func.sum(
                    case(
                        (
                            and_(
                                observation.succeeded.is_(False),
                                observation.failure_kind
                                == "unavailable",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("unavailable"),
                func.sum(
                    case(
                        (
                            and_(
                                observation.succeeded.is_(False),
                                observation.failure_kind
                                == "circuit_open",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("circuit_open"),
                func.sum(
                    case(
                        (
                            and_(
                                observation.succeeded.is_(False),
                                observation.failure_kind
                                == "provider_error",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("provider_errors"),
                func.sum(
                    case(
                        (
                            and_(
                                observation.succeeded.is_(False),
                                observation.failure_kind.notin_(
                                    [
                                        "timeout",
                                        "unavailable",
                                        "circuit_open",
                                        "provider_error",
                                    ]
                                ),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("other_failures"),
                func.sum(
                    case(
                        (
                            and_(
                                observation.succeeded.is_(False),
                                observation.fallback_allowed
                                .is_(True),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("fallback_eligible_failures"),
                func.sum(
                    case(
                        (
                            and_(
                                observation.succeeded.is_(False),
                                observation.fallback_allowed
                                .is_(True),
                                fallback_recovered,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("fallback_recoveries"),
                func.count(
                    func.distinct(
                        case(
                            (
                                observation.fallback_used
                                .is_(True),
                                observation.source_event_id,
                            ),
                            else_=None,
                        )
                    )
                ).label("fallback_invocations"),
                func.coalesce(
                    func.avg(observation.duration_ms),
                    0.0,
                ).label("average_duration_ms"),
            )
            .join(
                PlatformEvent,
                PlatformEvent.id
                == observation.source_event_id,
            )
            .where(*filters)
            .group_by(
                capability_expression,
                observation.provider_id,
                observation.provider_ref,
                observation.tenant_id,
            )
            .order_by(
                capability_expression,
                observation.provider_id,
                observation.provider_ref,
                observation.tenant_id,
            )
        )

        result = await self.db.execute(stmt)
        return (
            window_start,
            window_end,
            [dict(row) for row in result.mappings().all()],
        )

    async def list_observations(
        self,
        *,
        user_id,
        window_hours: int = 24,
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        tenant_id: str | None = None,
        failure_kind: str | None = None,
        correlation_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
        now: datetime | None = None,
    ) -> tuple[datetime, datetime, list[
        CapabilityPerformanceObservationRecord
    ]]:
        normalized_user_id = _normalize_user_id(user_id)
        window_end = now or datetime.now(timezone.utc)

        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=timezone.utc)

        window_start = window_end - timedelta(
            hours=window_hours
        )

        observation = CapabilityPerformanceObservationRecord
        capability_expression = func.coalesce(
            observation.resolved_capability_id,
            observation.requested_capability_id,
        )

        filters = [
            PlatformEvent.user_id == normalized_user_id,
            observation.observed_at >= window_start,
            observation.observed_at < window_end,
        ]

        if capability_id is not None:
            filters.append(
                capability_expression == capability_id
            )

        if provider_id is not None:
            filters.append(
                observation.provider_id == provider_id
            )

        if provider_ref is not None:
            filters.append(
                observation.provider_ref == provider_ref
            )

        if tenant_id is not None:
            filters.append(
                observation.tenant_id == tenant_id
            )

        if failure_kind is not None:
            filters.append(
                observation.failure_kind == failure_kind
            )

        if correlation_id is not None:
            filters.append(
                observation.correlation_id == correlation_id
            )

        stmt = (
            select(observation)
            .join(
                PlatformEvent,
                PlatformEvent.id
                == observation.source_event_id,
            )
            .where(*filters)
            .order_by(
                observation.observed_at.desc(),
                observation.source_event_id.desc(),
                observation.attempt_index.asc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)

        return (
            window_start,
            window_end,
            list(result.scalars().all()),
        )


__all__ = ["CapabilityPerformanceQueryRepository"]
