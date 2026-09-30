from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.tcos.planner.runtime.advisory_context_injection import (
    ADVISORY_PREFERENCE_KEY,
)
from app.tcos.planner.runtime.plan_candidate import (
    PlanCandidate,
)
from app.tcos.planner.runtime.planning_context import (
    PlanningContext,
)


ADVISORY_OBSERVATION_KEY = (
    "learning_advisory_observation"
)


class PlannerAdvisoryObservation(BaseModel):
    """
    Read-only record that advisory context was available to planning.

    This observation never changes candidate scores, candidate ordering,
    selected capabilities, BusinessPlan content, approval, verification,
    or execution behavior.
    """

    model_config = ConfigDict(extra="forbid")

    available: bool = False
    injected: bool = False
    fragment_count: int = Field(
        default=0,
        ge=0,
    )

    informational_only: bool = True
    affects_score: bool = False
    affects_ordering: bool = False
    affects_capability_selection: bool = False
    affects_business_plan: bool = False
    authorizes_execution: bool = False
    bypasses_approval: bool = False
    bypasses_verification: bool = False

    source_promotion_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_safety_boundary(self):
        if not self.informational_only:
            raise ValueError(
                "Planner advisory observation must "
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
                "Planner advisory observation cannot "
                "alter planning or execution"
            )

        if self.injected and not self.available:
            raise ValueError(
                "Injected advisory observation must "
                "also be available"
            )

        if self.injected and self.fragment_count < 1:
            raise ValueError(
                "Injected advisory observation requires "
                "at least one fragment"
            )

        if not self.injected and self.fragment_count != 0:
            raise ValueError(
                "Non-injected advisory observation "
                "cannot report fragments"
            )

        return self


class PlannerAdvisoryObserver:
    """
    Adds read-only advisory availability metadata to plan candidates.

    Candidate objects and their nested BusinessPlan values are deep-copied.
    Existing metrics are preserved. Score and plan fields are never changed.
    """

    observation_key = ADVISORY_OBSERVATION_KEY

    def observe(
        self,
        *,
        candidates: list[PlanCandidate],
        context: PlanningContext | None,
    ) -> list[PlanCandidate]:
        observation = self._observation(
            context=context
        )

        observed: list[PlanCandidate] = []

        for candidate in candidates:
            copied = candidate.model_copy(
                deep=True
            )
            metrics = deepcopy(copied.metrics)
            metrics[self.observation_key] = (
                observation.model_dump(
                    mode="json"
                )
            )
            copied.metrics = metrics
            observed.append(copied)

        return observed

    def _observation(
        self,
        *,
        context: PlanningContext | None,
    ) -> PlannerAdvisoryObservation:
        if context is None:
            return PlannerAdvisoryObservation()

        raw = context.planner_preferences.get(
            ADVISORY_PREFERENCE_KEY
        )

        if not isinstance(raw, dict):
            return PlannerAdvisoryObservation()

        fragments = raw.get("fragments")

        if not isinstance(fragments, list):
            fragments = []

        present_fragments = [
            fragment
            for fragment in fragments
            if (
                isinstance(fragment, dict)
                and isinstance(
                    fragment.get("text"),
                    str,
                )
                and fragment["text"].strip()
            )
        ]

        enabled = raw.get("enabled") is True
        injected = (
            enabled
            and bool(present_fragments)
        )

        return PlannerAdvisoryObservation(
            available=injected,
            injected=injected,
            fragment_count=(
                len(present_fragments)
                if injected
                else 0
            ),
            source_promotion_ids=(
                self._source_promotion_ids(
                    present_fragments
                )
                if injected
                else ()
            ),
        )

    @staticmethod
    def _source_promotion_ids(
        fragments: list[dict[str, Any]],
    ) -> tuple[str, ...]:
        values: set[str] = set()

        for fragment in fragments:
            payload = fragment.get("payload")

            if not isinstance(payload, dict):
                continue

            raw_ids = payload.get(
                "source_promotion_ids"
            )

            if not isinstance(raw_ids, list):
                continue

            for value in raw_ids:
                normalized = str(value).strip()

                if normalized:
                    values.add(normalized)

        return tuple(sorted(values))


__all__ = [
    "ADVISORY_OBSERVATION_KEY",
    "PlannerAdvisoryObservation",
    "PlannerAdvisoryObserver",
]
