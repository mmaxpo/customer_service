from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.runtime.capabilities.execution.learning.insight_candidates import (
    CapabilityLearningInsightKind,
)
from app.runtime.capabilities.execution.learning.insight_promotions import (
    CapabilityLearningInsightPromotion,
    CapabilityLearningPromotionStatus,
)
from app.runtime.capabilities.execution.learning.insight_candidates import (
    CapabilityLearningPromotionTarget,
)


class CapabilityPlannerAdvisoryKind(StrEnum):
    GUIDANCE = "guidance"
    WARNING = "warning"


class CapabilityPlannerAdvisoryScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = None
    capability_id: str
    provider_id: str | None = None
    provider_ref: str | None = None
    action: str | None = None

    def exact_key(self) -> tuple[
        str | None,
        str,
        str | None,
        str | None,
        str | None,
    ]:
        return (
            self.tenant_id,
            self.capability_id,
            self.provider_id,
            self.provider_ref,
            self.action,
        )


class CapabilityPlannerAdvisoryProvenance(
    BaseModel
):
    model_config = ConfigDict(extra="forbid")

    promotion_id: UUID
    promotion_event_version: int = Field(ge=1)
    candidate_id: UUID
    candidate_version: int = Field(ge=1)
    evidence_fingerprint: str = Field(
        min_length=64,
        max_length=64,
    )
    promoted_at: datetime
    created_by_user_id: UUID


class CapabilityPlannerAdvisory(BaseModel):
    """
    Read-only planner context derived from one active promotion.

    This object carries guidance or warning text only. It has no authority to
    execute capabilities, select providers, alter scores, bypass approval,
    change runtime policy, or suppress verification.
    """

    model_config = ConfigDict(extra="forbid")

    advisory_kind: CapabilityPlannerAdvisoryKind
    scope: CapabilityPlannerAdvisoryScope

    statement: str = Field(min_length=1)
    recommended_behavior: str = Field(
        min_length=1
    )
    limitations: tuple[str, ...] = ()

    provenance: CapabilityPlannerAdvisoryProvenance

    read_only: bool = True
    affects_ranking: bool = False
    authorizes_execution: bool = False
    bypasses_verification: bool = False

    @model_validator(mode="after")
    def validate_safety_boundary(self):
        if not self.read_only:
            raise ValueError(
                "Planner advisory must remain "
                "read-only"
            )

        if self.affects_ranking:
            raise ValueError(
                "Planner advisory cannot affect "
                "ranking in this phase"
            )

        if self.authorizes_execution:
            raise ValueError(
                "Planner advisory cannot authorize "
                "execution"
            )

        if self.bypasses_verification:
            raise ValueError(
                "Planner advisory cannot bypass "
                "verification"
            )

        return self


class CapabilityPlannerAdvisoryProjection:
    @staticmethod
    def from_promotion(
        promotion: CapabilityLearningInsightPromotion,
    ) -> CapabilityPlannerAdvisory:
        if (
            promotion.status
            != CapabilityLearningPromotionStatus
            .ACTIVE
        ):
            raise ValueError(
                "Only active promotions can be "
                "projected"
            )

        if (
            promotion.promotion_target
            != CapabilityLearningPromotionTarget
            .PLANNER_ADVISORY
        ):
            raise ValueError(
                "Promotion target is not "
                "planner_advisory"
            )

        candidate_payload = (
            promotion.promotion_payload.get(
                "candidate"
            )
        )

        if not isinstance(
            candidate_payload,
            dict,
        ):
            raise ValueError(
                "Promotion does not contain a "
                "candidate snapshot"
            )

        kind = CapabilityLearningInsightKind(
            candidate_payload["kind"]
        )

        advisory_kind = (
            CapabilityPlannerAdvisoryKind.GUIDANCE
            if kind
            == CapabilityLearningInsightKind
            .POSITIVE_OUTCOME_PATTERN
            else CapabilityPlannerAdvisoryKind
            .WARNING
        )

        candidate_scope = (
            candidate_payload.get("scope")
            or {}
        )

        scope = CapabilityPlannerAdvisoryScope(
            tenant_id=candidate_scope.get(
                "tenant_id"
            ),
            capability_id=candidate_scope[
                "capability_id"
            ],
            provider_id=candidate_scope.get(
                "provider_id"
            ),
            provider_ref=candidate_scope.get(
                "provider_ref"
            ),
            action=candidate_scope.get(
                "action"
            ),
        )

        promotion_scope = (
            promotion.tenant_id,
            promotion.capability_id,
            promotion.provider_id,
            promotion.provider_ref,
            promotion.action,
        )

        if scope.exact_key() != promotion_scope:
            raise ValueError(
                "Candidate snapshot scope does not "
                "match promotion scope"
            )

        return CapabilityPlannerAdvisory(
            advisory_kind=advisory_kind,
            scope=scope,
            statement=str(
                candidate_payload["statement"]
            ),
            recommended_behavior=str(
                candidate_payload[
                    "recommended_behavior"
                ]
            ),
            limitations=tuple(
                candidate_payload.get(
                    "limitations"
                )
                or ()
            ),
            provenance=(
                CapabilityPlannerAdvisoryProvenance(
                    promotion_id=(
                        promotion.promotion_id
                    ),
                    promotion_event_version=(
                        promotion.event_version
                    ),
                    candidate_id=(
                        promotion.candidate_id
                    ),
                    candidate_version=(
                        promotion.candidate_version
                    ),
                    evidence_fingerprint=(
                        promotion
                        .evidence_fingerprint
                    ),
                    promoted_at=(
                        promotion.created_at
                    ),
                    created_by_user_id=(
                        promotion
                        .created_by_user_id
                    ),
                )
            ),
        )


__all__ = [
    "CapabilityPlannerAdvisory",
    "CapabilityPlannerAdvisoryKind",
    "CapabilityPlannerAdvisoryProjection",
    "CapabilityPlannerAdvisoryProvenance",
    "CapabilityPlannerAdvisoryScope",
]
