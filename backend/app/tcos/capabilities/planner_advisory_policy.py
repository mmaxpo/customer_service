from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.runtime.capabilities.execution.learning import (
    CapabilityPlannerAdvisory,
    CapabilityPlannerAdvisoryKind,
)


class CapabilityPlannerContextItemKind(
    StrEnum
):
    CONSIDERATION = "consideration"
    CAUTION = "caution"
    CONSTRAINT = "constraint"


class CapabilityPlannerContextSource(
    BaseModel
):
    model_config = ConfigDict(extra="forbid")

    promotion_id: UUID
    candidate_id: UUID
    evidence_fingerprint: str = Field(
        min_length=64,
        max_length=64,
    )


class CapabilityPlannerContextItem(
    BaseModel
):
    model_config = ConfigDict(extra="forbid")

    kind: CapabilityPlannerContextItemKind
    text: str = Field(min_length=1)
    source: CapabilityPlannerContextSource

    informational_only: bool = True
    ranking_delta: float = 0.0
    authorizes_execution: bool = False

    @model_validator(mode="after")
    def validate_non_authoritative(self):
        if not self.informational_only:
            raise ValueError(
                "Planner context must remain "
                "informational only"
            )

        if self.ranking_delta != 0.0:
            raise ValueError(
                "Planner context cannot change "
                "ranking"
            )

        if self.authorizes_execution:
            raise ValueError(
                "Planner context cannot authorize "
                "execution"
            )

        return self


class CapabilityPlannerAdvisoryContext(
    BaseModel
):
    model_config = ConfigDict(extra="forbid")

    considerations: tuple[
        CapabilityPlannerContextItem,
        ...,
    ] = ()
    cautions: tuple[
        CapabilityPlannerContextItem,
        ...,
    ] = ()
    constraints: tuple[
        CapabilityPlannerContextItem,
        ...,
    ] = ()

    source_promotion_ids: tuple[UUID, ...] = ()

    advisory_count: int = Field(
        default=0,
        ge=0,
    )

    informational_only: bool = True
    affects_ranking: bool = False
    affects_compatibility: bool = False
    selects_provider: bool = False
    authorizes_execution: bool = False
    bypasses_approval: bool = False
    bypasses_verification: bool = False

    @model_validator(mode="after")
    def validate_safety_boundary(self):
        if not self.informational_only:
            raise ValueError(
                "Advisory context must remain "
                "informational only"
            )

        forbidden = (
            self.affects_ranking,
            self.affects_compatibility,
            self.selects_provider,
            self.authorizes_execution,
            self.bypasses_approval,
            self.bypasses_verification,
        )

        if any(forbidden):
            raise ValueError(
                "Advisory context cannot alter "
                "planner or execution decisions"
            )

        return self


class CapabilityPlannerAdvisoryPolicy:
    """
    Deterministically converts raw advisories into structured planner context.

    The resulting context is descriptive only. It does not modify planner
    ranking, compatibility, provider resolution, approval, verification, or
    capability execution.
    """

    def __init__(
        self,
        *,
        maximum_items_per_section: int = 25,
    ) -> None:
        if (
            maximum_items_per_section < 1
            or maximum_items_per_section > 100
        ):
            raise ValueError(
                "maximum_items_per_section must "
                "be between 1 and 100"
            )

        self.maximum_items_per_section = (
            maximum_items_per_section
        )

    def consume(
        self,
        advisories: list[
            CapabilityPlannerAdvisory
        ],
    ) -> CapabilityPlannerAdvisoryContext:
        ordered = sorted(
            advisories,
            key=lambda item: (
                str(
                    item.provenance
                    .promotion_id
                ),
                item.advisory_kind.value,
                item.statement,
            ),
        )

        considerations: list[
            CapabilityPlannerContextItem
        ] = []
        cautions: list[
            CapabilityPlannerContextItem
        ] = []
        constraints: list[
            CapabilityPlannerContextItem
        ] = []

        seen_considerations: set[
            tuple[str, UUID]
        ] = set()
        seen_cautions: set[
            tuple[str, UUID]
        ] = set()
        seen_constraints: set[
            tuple[str, UUID]
        ] = set()

        for advisory in ordered:
            source = _source(advisory)

            if (
                advisory.advisory_kind
                == CapabilityPlannerAdvisoryKind
                .GUIDANCE
            ):
                _append_unique(
                    items=considerations,
                    seen=seen_considerations,
                    item=CapabilityPlannerContextItem(
                        kind=(
                            CapabilityPlannerContextItemKind
                            .CONSIDERATION
                        ),
                        text=(
                            advisory
                            .recommended_behavior
                        ),
                        source=source,
                    ),
                    maximum=(
                        self
                        .maximum_items_per_section
                    ),
                )
            else:
                _append_unique(
                    items=cautions,
                    seen=seen_cautions,
                    item=CapabilityPlannerContextItem(
                        kind=(
                            CapabilityPlannerContextItemKind
                            .CAUTION
                        ),
                        text=advisory.statement,
                        source=source,
                    ),
                    maximum=(
                        self
                        .maximum_items_per_section
                    ),
                )

            for limitation in advisory.limitations:
                normalized = limitation.strip()
                if not normalized:
                    continue

                _append_unique(
                    items=constraints,
                    seen=seen_constraints,
                    item=CapabilityPlannerContextItem(
                        kind=(
                            CapabilityPlannerContextItemKind
                            .CONSTRAINT
                        ),
                        text=normalized,
                        source=source,
                    ),
                    maximum=(
                        self
                        .maximum_items_per_section
                    ),
                )

        source_promotion_ids = tuple(
            sorted(
                {
                    advisory
                    .provenance
                    .promotion_id
                    for advisory in ordered
                },
                key=str,
            )
        )

        return CapabilityPlannerAdvisoryContext(
            considerations=tuple(
                considerations
            ),
            cautions=tuple(cautions),
            constraints=tuple(constraints),
            source_promotion_ids=(
                source_promotion_ids
            ),
            advisory_count=len(ordered),
        )


def _source(
    advisory: CapabilityPlannerAdvisory,
) -> CapabilityPlannerContextSource:
    return CapabilityPlannerContextSource(
        promotion_id=(
            advisory.provenance.promotion_id
        ),
        candidate_id=(
            advisory.provenance.candidate_id
        ),
        evidence_fingerprint=(
            advisory
            .provenance
            .evidence_fingerprint
        ),
    )


def _append_unique(
    *,
    items: list[
        CapabilityPlannerContextItem
    ],
    seen: set[tuple[str, UUID]],
    item: CapabilityPlannerContextItem,
    maximum: int,
) -> None:
    if len(items) >= maximum:
        return

    key = (
        item.text,
        item.source.promotion_id,
    )

    if key in seen:
        return

    seen.add(key)
    items.append(item)


__all__ = [
    "CapabilityPlannerAdvisoryContext",
    "CapabilityPlannerAdvisoryPolicy",
    "CapabilityPlannerContextItem",
    "CapabilityPlannerContextItemKind",
    "CapabilityPlannerContextSource",
]
