from __future__ import annotations

from typing import Any

from app.runtime.capabilities.execution.outcomes import (
    CapabilityExecutionOutcome,
)
from app.runtime.capabilities.execution.performance.models import (
    CapabilityPerformanceProjector,
)
from app.runtime.capabilities.execution.performance.repository import (
    CapabilityPerformanceObservationRepository,
)


def capability_outcome_from_platform_event(
    event: Any,
) -> CapabilityExecutionOutcome:
    payload = dict(event.payload or {})
    meta = dict(event.meta or {})

    invocation_metadata = dict(
        meta.get("invocation_metadata") or {}
    )

    for key in (
        "workflow_run_id",
        "planner_session_id",
        "thread_id",
    ):
        if (
            key not in invocation_metadata
            and meta.get(key) is not None
        ):
            invocation_metadata[key] = meta[key]

    return CapabilityExecutionOutcome(
        correlation_id=(
            meta.get("correlation_id")
            or payload.get("correlation_id")
            or str(event.id)
        ),
        requested_capability_id=(
            payload["requested_capability_id"]
        ),
        resolved_capability_id=payload.get(
            "resolved_capability_id"
        ),
        status=payload["status"],
        ok=bool(payload.get("ok")),
        selected_provider_id=payload.get(
            "selected_provider_id"
        ),
        provider_ref=payload.get("provider_ref"),
        fallback_used=bool(
            payload.get("fallback_used")
        ),
        attempts=payload.get("attempts") or [],
        error_code=payload.get("error_code"),
        error_message=payload.get("error_message"),
        failure_kind=payload.get("failure_kind"),
        exception_type=payload.get("exception_type"),
        duration_ms=payload.get("duration_ms"),
        user_id=(
            str(event.user_id)
            if event.user_id is not None
            else None
        ),
        tenant_id=(
            str(meta["tenant_id"])
            if meta.get("tenant_id") is not None
            else None
        ),
        invocation_metadata=invocation_metadata,
        result_metadata={},
        verification_context=(
            payload.get("verification_context")
        ),
        created_at_ts=float(
            payload.get("created_at_ts")
            or event.created_at.timestamp()
        ),
    )


class DurableCapabilityPerformanceProjector:
    def __init__(
        self,
        *,
        repository: CapabilityPerformanceObservationRepository,
        projector: CapabilityPerformanceProjector | None = None,
    ) -> None:
        self.repository = repository
        self.projector = (
            projector or CapabilityPerformanceProjector()
        )

    async def project_event(self, event: Any) -> dict[str, Any]:
        outcome = capability_outcome_from_platform_event(
            event
        )
        observations = self.projector.project(outcome)

        inserted_count = await self.repository.record_many(
            source_event_id=event.id,
            observations=observations,
        )

        return {
            "source_event_id": str(event.id),
            "correlation_id": outcome.correlation_id,
            "projected_count": len(observations),
            "inserted_count": inserted_count,
            "duplicate_count": (
                len(observations) - inserted_count
            ),
        }


__all__ = [
    "DurableCapabilityPerformanceProjector",
    "capability_outcome_from_platform_event",
]
