from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.runtime.capabilities.execution.learning.insight_candidates import (
    CapabilityLearningApprovalStatus,
    CapabilityLearningCandidateStatus,
    CapabilityLearningInsightCandidate,
    CapabilityLearningPromotionTarget,
)


class CapabilityLearningPromotionEventType(StrEnum):
    PROMOTED = "promoted"
    REVOKED = "revoked"


class CapabilityLearningPromotionStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class CapabilityLearningInsightPromotion(BaseModel):
    """
    Immutable event in one explicit promotion lifecycle.

    Promotion records are advisory registry entries only. They do not alter
    planner behavior, provider selection, traffic allocation, health, or
    runtime policy.
    """

    model_config = ConfigDict(extra="forbid")

    promotion_id: UUID = Field(
        default_factory=uuid4
    )
    event_version: int = Field(
        default=1,
        ge=1,
    )

    candidate_id: UUID
    candidate_version: int = Field(ge=1)

    user_id: UUID

    tenant_id: str | None = None
    capability_id: str
    provider_id: str | None = None
    provider_ref: str | None = None
    action: str | None = None

    event_type: CapabilityLearningPromotionEventType
    status: CapabilityLearningPromotionStatus

    promotion_target: CapabilityLearningPromotionTarget
    evidence_fingerprint: str = Field(
        min_length=64,
        max_length=64,
    )

    reason: str = Field(
        min_length=1,
        max_length=4000,
    )
    created_by_user_id: UUID
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    promotion_payload: dict = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def validate_transition(self):
        expected_status = (
            CapabilityLearningPromotionStatus.ACTIVE
            if self.event_type
            == CapabilityLearningPromotionEventType
            .PROMOTED
            else CapabilityLearningPromotionStatus
            .REVOKED
        )

        if self.status != expected_status:
            raise ValueError(
                "promotion status must match "
                "promotion event type"
            )

        if (
            self.event_type
            == CapabilityLearningPromotionEventType
            .PROMOTED
            and self.event_version != 1
        ):
            raise ValueError(
                "promoted event must be version 1"
            )

        if (
            self.event_type
            == CapabilityLearningPromotionEventType
            .REVOKED
            and self.event_version != 2
        ):
            raise ValueError(
                "revoked event must be version 2"
            )

        return self


class CapabilityLearningPromotionFactory:
    @staticmethod
    def promote(
        *,
        user_id: UUID,
        candidate: CapabilityLearningInsightCandidate,
        created_by_user_id: UUID,
        reason: str,
        created_at: datetime | None = None,
    ) -> CapabilityLearningInsightPromotion:
        _validate_candidate_for_promotion(
            candidate
        )

        return CapabilityLearningInsightPromotion(
            candidate_id=candidate.candidate_id,
            candidate_version=(
                candidate.candidate_version
            ),
            user_id=user_id,
            tenant_id=candidate.scope.tenant_id,
            capability_id=(
                candidate.scope.capability_id
            ),
            provider_id=candidate.scope.provider_id,
            provider_ref=candidate.scope.provider_ref,
            action=candidate.scope.action,
            event_type=(
                CapabilityLearningPromotionEventType
                .PROMOTED
            ),
            status=(
                CapabilityLearningPromotionStatus
                .ACTIVE
            ),
            promotion_target=(
                candidate.promotion_target
            ),
            evidence_fingerprint=(
                candidate
                .evidence
                .evidence_fingerprint
            ),
            reason=reason,
            created_by_user_id=(
                created_by_user_id
            ),
            created_at=_aware(created_at),
            promotion_payload={
                "candidate": candidate.model_dump(
                    mode="json"
                ),
            },
        )

    @staticmethod
    def revoke(
        *,
        current: CapabilityLearningInsightPromotion,
        created_by_user_id: UUID,
        reason: str,
        created_at: datetime | None = None,
    ) -> CapabilityLearningInsightPromotion:
        if (
            current.event_type
            != CapabilityLearningPromotionEventType
            .PROMOTED
            or current.status
            != CapabilityLearningPromotionStatus
            .ACTIVE
            or current.event_version != 1
        ):
            raise ValueError(
                "Only an active promotion can "
                "be revoked"
            )

        return CapabilityLearningInsightPromotion(
            promotion_id=current.promotion_id,
            event_version=2,
            candidate_id=current.candidate_id,
            candidate_version=(
                current.candidate_version
            ),
            user_id=current.user_id,
            tenant_id=current.tenant_id,
            capability_id=current.capability_id,
            provider_id=current.provider_id,
            provider_ref=current.provider_ref,
            action=current.action,
            event_type=(
                CapabilityLearningPromotionEventType
                .REVOKED
            ),
            status=(
                CapabilityLearningPromotionStatus
                .REVOKED
            ),
            promotion_target=(
                current.promotion_target
            ),
            evidence_fingerprint=(
                current.evidence_fingerprint
            ),
            reason=reason,
            created_by_user_id=(
                created_by_user_id
            ),
            created_at=_aware(created_at),
            promotion_payload={
                "revokes_event_version": (
                    current.event_version
                ),
                "original_promotion": (
                    current.model_dump(mode="json")
                ),
            },
        )


def _validate_candidate_for_promotion(
    candidate: CapabilityLearningInsightCandidate,
) -> None:
    if (
        candidate.status
        != CapabilityLearningCandidateStatus
        .APPROVED
    ):
        raise ValueError(
            "Candidate must be approved "
            "before promotion"
        )

    if (
        candidate.approval_status
        != CapabilityLearningApprovalStatus
        .APPROVED
    ):
        raise ValueError(
            "Candidate approval status must "
            "be approved"
        )

    if not candidate.validation_passed:
        raise ValueError(
            "Candidate must pass validation "
            "before promotion"
        )

    if not candidate.promotion_eligible:
        raise ValueError(
            "Candidate is not promotion eligible"
        )

    if candidate.blocking_reasons:
        raise ValueError(
            "Candidate has promotion blockers"
        )


def _aware(
    value: datetime | None,
) -> datetime:
    resolved = value or datetime.now(
        timezone.utc
    )

    if resolved.tzinfo is None:
        return resolved.replace(
            tzinfo=timezone.utc
        )

    return resolved


__all__ = [
    "CapabilityLearningInsightPromotion",
    "CapabilityLearningPromotionEventType",
    "CapabilityLearningPromotionFactory",
    "CapabilityLearningPromotionStatus",
]
