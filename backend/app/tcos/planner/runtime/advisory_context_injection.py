from __future__ import annotations

from copy import deepcopy

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.tcos.capabilities.planner_advisory_renderer import (
    CapabilityPlannerRenderedContext,
)
from app.tcos.planner.runtime.planning_context import (
    PlanningContext,
)


ADVISORY_PREFERENCE_KEY = "learning_advisories"


class PlannerAdvisoryInjectionResult(BaseModel):
    """
    Result of explicitly attaching advisory material to planner context.

    Injection is contextual only. The result does not instruct the planner to
    change ranking, capability selection, compatibility, approval,
    verification, or execution behavior.
    """

    model_config = ConfigDict(extra="forbid")

    context: PlanningContext

    requested: bool
    injected: bool

    fragment_count: int = Field(
        default=0,
        ge=0,
    )

    informational_only: bool = True
    affects_ranking: bool = False
    affects_capability_selection: bool = False
    affects_compatibility: bool = False
    authorizes_execution: bool = False
    bypasses_approval: bool = False
    bypasses_verification: bool = False

    @model_validator(mode="after")
    def validate_safety_boundary(self):
        if not self.informational_only:
            raise ValueError(
                "Injected advisory context must "
                "remain informational only"
            )

        if any(
            (
                self.affects_ranking,
                self.affects_capability_selection,
                self.affects_compatibility,
                self.authorizes_execution,
                self.bypasses_approval,
                self.bypasses_verification,
            )
        ):
            raise ValueError(
                "Advisory injection cannot alter "
                "planning or execution decisions"
            )

        if self.injected and not self.requested:
            raise ValueError(
                "Advisory context cannot be injected "
                "without an explicit request"
            )

        if self.injected and self.fragment_count < 1:
            raise ValueError(
                "Injected advisory context requires "
                "at least one fragment"
            )

        if not self.injected and self.fragment_count != 0:
            raise ValueError(
                "Non-injected result cannot report "
                "injected fragments"
            )

        return self


class PlannerAdvisoryContextInjector:
    """
    Explicitly attaches rendered learning advisories to PlanningContext.

    The injector never mutates the supplied PlanningContext. It writes only to
    the reserved planner_preferences["learning_advisories"] namespace and does
    not modify user input, enabled capabilities, execution constraints, planner
    scoring, capability selection, or execution.
    """

    preference_key = ADVISORY_PREFERENCE_KEY

    def inject(
        self,
        *,
        context: PlanningContext,
        rendered_contexts: list[
            CapabilityPlannerRenderedContext
        ],
        enabled: bool = False,
    ) -> PlannerAdvisoryInjectionResult:
        if not enabled:
            return PlannerAdvisoryInjectionResult(
                context=context.model_copy(deep=True),
                requested=False,
                injected=False,
                fragment_count=0,
            )

        present_contexts = [
            item
            for item in rendered_contexts
            if item.present and item.text.strip()
        ]

        if not present_contexts:
            return PlannerAdvisoryInjectionResult(
                context=context.model_copy(deep=True),
                requested=True,
                injected=False,
                fragment_count=0,
            )

        updated = context.model_copy(deep=True)
        preferences = deepcopy(
            updated.planner_preferences
        )

        preferences[self.preference_key] = {
            "enabled": True,
            "informational_only": True,
            "affects_ranking": False,
            "affects_capability_selection": False,
            "affects_compatibility": False,
            "authorizes_execution": False,
            "bypasses_approval": False,
            "bypasses_verification": False,
            "fragments": [
                {
                    "text": item.text,
                    "payload": deepcopy(
                        item.payload
                    ),
                }
                for item in present_contexts
            ],
        }

        updated.planner_preferences = preferences

        return PlannerAdvisoryInjectionResult(
            context=updated,
            requested=True,
            injected=True,
            fragment_count=len(present_contexts),
        )


__all__ = [
    "ADVISORY_PREFERENCE_KEY",
    "PlannerAdvisoryContextInjector",
    "PlannerAdvisoryInjectionResult",
]
