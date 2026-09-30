from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.tcos.planner.runtime.advisory_observation import (
    ADVISORY_OBSERVATION_KEY,
)
from app.tcos.planner.runtime.plan_candidate import (
    PlanCandidate,
)


PLANNER_ADVISORY_OBSERVED_EVENT = (
    "planner.advisory_context_observed"
)


class PlannerAdvisorySessionTelemetry(
    BaseModel
):
    """
    Session-level projection of the selected candidate's advisory observation.

    Telemetry describes what context was available during planning. It cannot
    modify candidate scoring, ordering, capability selection, BusinessPlan
    content, verification, repair, compilation, approval, or execution.
    """

    model_config = ConfigDict(extra="forbid")

    available: bool = False
    injected: bool = False
    fragment_count: int = Field(
        default=0,
        ge=0,
    )
    source_promotion_ids: tuple[str, ...] = ()

    informational_only: bool = True
    affects_score: bool = False
    affects_ordering: bool = False
    affects_capability_selection: bool = False
    affects_business_plan: bool = False
    authorizes_execution: bool = False
    bypasses_approval: bool = False
    bypasses_verification: bool = False

    @model_validator(mode="after")
    def validate_safety_boundary(self):
        if not self.informational_only:
            raise ValueError(
                "Planner advisory telemetry must "
                "remain informational only"
            )

        if any(
            (
                self.affects_score,
                self.affects_ordering,
                self.affects_capability_selection,
                self.affects_business_plan,
                self.authorizes_execution,
                self.bypasses_approval,
                self.bypasses_verification,
            )
        ):
            raise ValueError(
                "Planner advisory telemetry cannot "
                "alter planning or execution"
            )

        if self.injected and not self.available:
            raise ValueError(
                "Injected planner advisory telemetry "
                "must also be available"
            )

        if self.injected and self.fragment_count < 1:
            raise ValueError(
                "Injected planner advisory telemetry "
                "requires at least one fragment"
            )

        if not self.injected and self.fragment_count != 0:
            raise ValueError(
                "Non-injected planner advisory telemetry "
                "cannot report fragments"
            )

        return self

    def metric_fields(
        self,
    ) -> dict[str, Any]:
        return {
            "advisory_context_available": (
                self.available
            ),
            "advisory_context_injected": (
                self.injected
            ),
            "advisory_fragment_count": (
                self.fragment_count
            ),
            "advisory_source_promotion_ids": (
                list(self.source_promotion_ids)
            ),
            "advisory_informational_only": (
                self.informational_only
            ),
            "advisory_affects_score": (
                self.affects_score
            ),
            "advisory_affects_ordering": (
                self.affects_ordering
            ),
            "advisory_affects_capability_selection": (
                self.affects_capability_selection
            ),
            "advisory_affects_business_plan": (
                self.affects_business_plan
            ),
            "advisory_authorizes_execution": (
                self.authorizes_execution
            ),
            "advisory_bypasses_approval": (
                self.bypasses_approval
            ),
            "advisory_bypasses_verification": (
                self.bypasses_verification
            ),
        }


class PlannerAdvisoryTelemetryProjector:
    """
    Reads advisory observation metadata from the selected candidate.

    The candidate is never modified.
    """

    def project(
        self,
        *,
        candidate: PlanCandidate,
    ) -> PlannerAdvisorySessionTelemetry:
        raw = candidate.metrics.get(
            ADVISORY_OBSERVATION_KEY
        )

        if not isinstance(raw, dict):
            return PlannerAdvisorySessionTelemetry()

        source_ids = raw.get(
            "source_promotion_ids"
        )

        if not isinstance(
            source_ids,
            (list, tuple),
        ):
            source_ids = ()

        normalized_source_ids = tuple(
            sorted(
                {
                    str(value).strip()
                    for value in source_ids
                    if str(value).strip()
                }
            )
        )

        return PlannerAdvisorySessionTelemetry(
            available=raw.get("available") is True,
            injected=raw.get("injected") is True,
            fragment_count=int(
                raw.get("fragment_count", 0)
                or 0
            ),
            source_promotion_ids=(
                normalized_source_ids
            ),
        )


__all__ = [
    "PLANNER_ADVISORY_OBSERVED_EVENT",
    "PlannerAdvisorySessionTelemetry",
    "PlannerAdvisoryTelemetryProjector",
]
