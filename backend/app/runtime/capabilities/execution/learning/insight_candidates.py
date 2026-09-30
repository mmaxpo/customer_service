from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.runtime.capabilities.execution.learning.aggregation import (
    CapabilityLearningInterpretation,
    CapabilityLearningQualityLevel,
    CapabilityLearningSummary,
)
from app.runtime.capabilities.execution.learning.trends import (
    CapabilityLearningAdvisoryStatus,
    CapabilityLearningStabilityLevel,
    CapabilityLearningTrendDirection,
    CapabilityLearningTrendReport,
)


class CapabilityLearningInsightKind(StrEnum):
    POSITIVE_OUTCOME_PATTERN = (
        "positive_outcome_pattern"
    )
    NEGATIVE_OUTCOME_PATTERN = (
        "negative_outcome_pattern"
    )


class CapabilityLearningCandidateStatus(StrEnum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    BLOCKED = "blocked"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROMOTED = "promoted"
    REVOKED = "revoked"


class CapabilityLearningApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CapabilityLearningPromotionTarget(StrEnum):
    PLANNER_ADVISORY = "planner_advisory"
    OPERATOR_GUIDANCE = "operator_guidance"


class CapabilityLearningValidationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    passed: bool
    explanation: str


class CapabilityLearningCandidateScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str
    provider_id: str | None = None
    provider_ref: str | None = None
    tenant_id: str | None = None
    action: str | None = None

    def scope_key(self) -> str:
        return "|".join(
            (
                self.capability_id,
                self.provider_id or "*",
                self.provider_ref or "*",
                self.tenant_id or "*",
                self.action or "*",
            )
        )


class CapabilityLearningEvidenceSnapshot(BaseModel):
    """
    Immutable source evidence carried by one candidate proposal.
    """

    model_config = ConfigDict(extra="forbid")

    historical_summary: CapabilityLearningSummary
    recent_summary: CapabilityLearningSummary
    trend_report: CapabilityLearningTrendReport

    evidence_fingerprint: str = Field(
        min_length=64,
        max_length=64,
    )

    @classmethod
    def from_trend_report(
        cls,
        report: CapabilityLearningTrendReport,
    ) -> CapabilityLearningEvidenceSnapshot:
        payload = report.model_dump(
            mode="json"
        )
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        fingerprint = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

        return cls(
            historical_summary=report.historical,
            recent_summary=report.recent,
            trend_report=report,
            evidence_fingerprint=fingerprint,
        )


class CapabilityLearningInsightCandidate(BaseModel):
    """
    Reviewable proposed learning insight.

    A candidate is not an active learned rule. Creation, validation, or
    approval does not modify planner behavior, provider selection, traffic
    allocation, provider health, or runtime policy.
    """

    model_config = ConfigDict(extra="forbid")

    candidate_id: UUID = Field(
        default_factory=uuid4
    )
    candidate_version: int = Field(
        default=1,
        ge=1,
    )

    kind: CapabilityLearningInsightKind
    scope: CapabilityLearningCandidateScope

    statement: str = Field(min_length=1)
    recommended_behavior: str = Field(
        min_length=1
    )
    limitations: tuple[str, ...] = ()

    evidence: CapabilityLearningEvidenceSnapshot

    validation_checks: tuple[
        CapabilityLearningValidationCheck,
        ...,
    ]
    validation_passed: bool

    approval_required: bool = True
    approval_status: (
        CapabilityLearningApprovalStatus
    ) = CapabilityLearningApprovalStatus.PENDING

    status: CapabilityLearningCandidateStatus

    promotion_target: (
        CapabilityLearningPromotionTarget
    )
    promotion_eligible: bool
    blocking_reasons: tuple[str, ...] = ()

    proposed_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
    validated_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by_user_id: UUID | None = None
    review_reason: str | None = None
    promoted_at: datetime | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self):
        check_result = all(
            check.passed
            for check in self.validation_checks
        )

        if check_result != self.validation_passed:
            raise ValueError(
                "validation_passed must match "
                "validation_checks"
            )

        if (
            self.status
            == CapabilityLearningCandidateStatus
            .VALIDATED
            and not self.validation_passed
        ):
            raise ValueError(
                "validated candidate must pass "
                "all validation checks"
            )

        if (
            self.status
            == CapabilityLearningCandidateStatus
            .APPROVED
            and self.approval_status
            != CapabilityLearningApprovalStatus
            .APPROVED
        ):
            raise ValueError(
                "approved candidate requires "
                "approved approval_status"
            )

        if (
            self.status
            == CapabilityLearningCandidateStatus
            .REJECTED
            and self.approval_status
            != CapabilityLearningApprovalStatus
            .REJECTED
        ):
            raise ValueError(
                "rejected candidate requires "
                "rejected approval_status"
            )

        if self.promotion_eligible:
            if not self.validation_passed:
                raise ValueError(
                    "promotion eligibility requires "
                    "validated evidence"
                )

            if (
                self.approval_required
                and self.approval_status
                != CapabilityLearningApprovalStatus
                .APPROVED
            ):
                raise ValueError(
                    "promotion eligibility requires "
                    "explicit approval"
                )

            if self.blocking_reasons:
                raise ValueError(
                    "promotion-eligible candidate "
                    "cannot have blocking reasons"
                )

        return self


class CapabilityLearningInsightPolicy:
    """
    Safety policy for proposing and promoting advisory learning candidates.
    """

    def __init__(
        self,
        *,
        minimum_summary_confidence: float = 0.80,
        maximum_contradiction_score: float = 0.20,
        require_high_quality: bool = True,
        require_stable_trend: bool = True,
        approval_required: bool = True,
    ) -> None:
        for name, value in (
            (
                "minimum_summary_confidence",
                minimum_summary_confidence,
            ),
            (
                "maximum_contradiction_score",
                maximum_contradiction_score,
            ),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1"
                )

        self.minimum_summary_confidence = (
            minimum_summary_confidence
        )
        self.maximum_contradiction_score = (
            maximum_contradiction_score
        )
        self.require_high_quality = bool(
            require_high_quality
        )
        self.require_stable_trend = bool(
            require_stable_trend
        )
        self.approval_required = bool(
            approval_required
        )


class CapabilityLearningInsightCandidateFactory:
    def __init__(
        self,
        *,
        policy: (
            CapabilityLearningInsightPolicy
            | None
        ) = None,
    ) -> None:
        self.policy = (
            policy
            or CapabilityLearningInsightPolicy()
        )

    def propose(
        self,
        *,
        report: CapabilityLearningTrendReport,
        promotion_target: (
            CapabilityLearningPromotionTarget
        ) = (
            CapabilityLearningPromotionTarget
            .PLANNER_ADVISORY
        ),
        proposed_at: datetime | None = None,
    ) -> CapabilityLearningInsightCandidate:
        recent = report.recent
        scope = CapabilityLearningCandidateScope(
            capability_id=report.capability_id,
            provider_id=report.provider_id,
            provider_ref=report.provider_ref,
            tenant_id=report.tenant_id,
            action=report.action,
        )

        kind = _kind_for_interpretation(
            recent.interpretation
        )

        checks = self._validation_checks(
            report=report,
            kind=kind,
        )
        validation_passed = all(
            check.passed
            for check in checks
        )

        blocking_reasons = tuple(
            check.code
            for check in checks
            if not check.passed
        )

        if validation_passed:
            status = (
                CapabilityLearningCandidateStatus
                .VALIDATED
            )
            validated_at = _aware(
                proposed_at
            )
        else:
            status = (
                CapabilityLearningCandidateStatus
                .BLOCKED
            )
            validated_at = None

        approval_status = (
            CapabilityLearningApprovalStatus
            .PENDING
        )

        if (
            validation_passed
            and self.policy.approval_required
        ):
            blocking_reasons = (
                *blocking_reasons,
                "explicit_approval_required",
            )

        return CapabilityLearningInsightCandidate(
            kind=kind,
            scope=scope,
            statement=_statement(
                kind=kind,
                scope=scope,
                recent=recent,
            ),
            recommended_behavior=(
                _recommended_behavior(
                    kind=kind,
                    scope=scope,
                )
            ),
            limitations=_limitations(
                report=report
            ),
            evidence=(
                CapabilityLearningEvidenceSnapshot
                .from_trend_report(report)
            ),
            validation_checks=checks,
            validation_passed=(
                validation_passed
            ),
            approval_required=(
                self.policy.approval_required
            ),
            approval_status=approval_status,
            status=status,
            promotion_target=promotion_target,
            promotion_eligible=False,
            blocking_reasons=(
                blocking_reasons
            ),
            proposed_at=_aware(proposed_at),
            validated_at=validated_at,
        )

    def review(
        self,
        *,
        candidate: CapabilityLearningInsightCandidate,
        approved: bool,
        reviewed_by_user_id: UUID,
        reason: str,
        reviewed_at: datetime | None = None,
    ) -> CapabilityLearningInsightCandidate:
        if candidate.status not in {
            CapabilityLearningCandidateStatus
            .VALIDATED,
            CapabilityLearningCandidateStatus
            .APPROVED,
            CapabilityLearningCandidateStatus
            .REJECTED,
        }:
            raise ValueError(
                "Only validated candidates can "
                "be reviewed"
            )

        resolved_at = _aware(reviewed_at)

        if not approved:
            return candidate.model_copy(
                update={
                    "candidate_version": (
                        candidate.candidate_version
                        + 1
                    ),
                    "approval_status": (
                        CapabilityLearningApprovalStatus
                        .REJECTED
                    ),
                    "status": (
                        CapabilityLearningCandidateStatus
                        .REJECTED
                    ),
                    "promotion_eligible": False,
                    "blocking_reasons": (
                        "approval_rejected",
                    ),
                    "reviewed_at": resolved_at,
                    "reviewed_by_user_id": (
                        reviewed_by_user_id
                    ),
                    "review_reason": reason,
                }
            )

        remaining_blockers = tuple(
            blocker
            for blocker in candidate.blocking_reasons
            if blocker
            != "explicit_approval_required"
        )

        eligible = (
            candidate.validation_passed
            and not remaining_blockers
        )

        return candidate.model_copy(
            update={
                "candidate_version": (
                    candidate.candidate_version
                    + 1
                ),
                "approval_status": (
                    CapabilityLearningApprovalStatus
                    .APPROVED
                ),
                "status": (
                    CapabilityLearningCandidateStatus
                    .APPROVED
                ),
                "promotion_eligible": eligible,
                "blocking_reasons": (
                    remaining_blockers
                ),
                "reviewed_at": resolved_at,
                "reviewed_by_user_id": (
                    reviewed_by_user_id
                ),
                "review_reason": reason,
            }
        )

    def _validation_checks(
        self,
        *,
        report: CapabilityLearningTrendReport,
        kind: CapabilityLearningInsightKind,
    ) -> tuple[
        CapabilityLearningValidationCheck,
        ...,
    ]:
        recent = report.recent

        return (
            _check(
                code="comparison_evidence_sufficient",
                passed=(
                    report
                    .comparison_evidence_sufficient
                ),
                explanation=(
                    "Both historical and recent "
                    "windows contain sufficient "
                    "effective evidence."
                ),
            ),
            _check(
                code="advisory_status_trusted",
                passed=(
                    report.advisory_status
                    == CapabilityLearningAdvisoryStatus
                    .TRUST
                ),
                explanation=(
                    "Trend analysis must classify "
                    "the evidence as trusted."
                ),
            ),
            _check(
                code="stable_learning_pattern",
                passed=(
                    not self.policy
                    .require_stable_trend
                    or (
                        report.stability_level
                        == CapabilityLearningStabilityLevel
                        .STABLE
                        and report.trend_direction
                        == CapabilityLearningTrendDirection
                        .STABLE
                    )
                ),
                explanation=(
                    "Promotion candidates require "
                    "a stable, non-moving pattern."
                ),
            ),
            _check(
                code="contradiction_within_limit",
                passed=(
                    report.contradiction_score
                    <= self.policy
                    .maximum_contradiction_score
                ),
                explanation=(
                    "Contradiction score must remain "
                    "within the configured safety limit."
                ),
            ),
            _check(
                code="recent_evidence_confident",
                passed=(
                    recent.summary_confidence
                    >= self.policy
                    .minimum_summary_confidence
                ),
                explanation=(
                    "Recent evidence must meet the "
                    "minimum confidence threshold."
                ),
            ),
            _check(
                code="recent_evidence_quality",
                passed=(
                    not self.policy.require_high_quality
                    or recent.quality_level
                    == CapabilityLearningQualityLevel
                    .HIGH
                ),
                explanation=(
                    "Recent evidence must have high "
                    "quality."
                ),
            ),
            _check(
                code="supported_interpretation",
                passed=(
                    kind
                    in {
                        CapabilityLearningInsightKind
                        .POSITIVE_OUTCOME_PATTERN,
                        CapabilityLearningInsightKind
                        .NEGATIVE_OUTCOME_PATTERN,
                    }
                ),
                explanation=(
                    "Only stable positive or negative "
                    "outcome patterns can become "
                    "candidates."
                ),
            ),
        )


def _kind_for_interpretation(
    interpretation: CapabilityLearningInterpretation,
) -> CapabilityLearningInsightKind:
    if (
        interpretation
        == CapabilityLearningInterpretation
        .POSITIVE
    ):
        return (
            CapabilityLearningInsightKind
            .POSITIVE_OUTCOME_PATTERN
        )

    if (
        interpretation
        == CapabilityLearningInterpretation
        .NEGATIVE
    ):
        return (
            CapabilityLearningInsightKind
            .NEGATIVE_OUTCOME_PATTERN
        )

    raise ValueError(
        "Only positive or negative stable "
        "interpretations can produce an "
        "insight candidate"
    )


def _check(
    *,
    code: str,
    passed: bool,
    explanation: str,
) -> CapabilityLearningValidationCheck:
    return CapabilityLearningValidationCheck(
        code=code,
        passed=bool(passed),
        explanation=explanation,
    )


def _statement(
    *,
    kind: CapabilityLearningInsightKind,
    scope: CapabilityLearningCandidateScope,
    recent: CapabilityLearningSummary,
) -> str:
    outcome = (
        "reliably produces the desired outcome"
        if kind
        == CapabilityLearningInsightKind
        .POSITIVE_OUTCOME_PATTERN
        else "reliably fails to produce the "
        "desired outcome"
    )

    return (
        f"Scope `{scope.scope_key()}` {outcome} "
        f"with estimated success rate "
        f"{recent.estimated_success_rate:.3f} "
        f"and confidence "
        f"{recent.summary_confidence:.3f}."
    )


def _recommended_behavior(
    *,
    kind: CapabilityLearningInsightKind,
    scope: CapabilityLearningCandidateScope,
) -> str:
    if (
        kind
        == CapabilityLearningInsightKind
        .POSITIVE_OUTCOME_PATTERN
    ):
        return (
            "Surface this pattern as advisory "
            "context when planning work for scope "
            f"`{scope.scope_key()}`."
        )

    return (
        "Surface a warning and require additional "
        "verification before planning similar work "
        f"for scope `{scope.scope_key()}`."
    )


def _limitations(
    *,
    report: CapabilityLearningTrendReport,
) -> tuple[str, ...]:
    return (
        "Evidence applies only to the exact "
        "candidate scope.",
        "Evidence applies only to the two "
        "captured time windows.",
        "The candidate is advisory and must not "
        "directly change runtime policy.",
        (
            "Observed contradiction score: "
            f"{report.contradiction_score:.3f}."
        ),
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
    "CapabilityLearningApprovalStatus",
    "CapabilityLearningCandidateScope",
    "CapabilityLearningCandidateStatus",
    "CapabilityLearningEvidenceSnapshot",
    "CapabilityLearningInsightCandidate",
    "CapabilityLearningInsightCandidateFactory",
    "CapabilityLearningInsightKind",
    "CapabilityLearningInsightPolicy",
    "CapabilityLearningPromotionTarget",
    "CapabilityLearningValidationCheck",
]
