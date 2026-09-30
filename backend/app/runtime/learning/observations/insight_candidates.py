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

from app.runtime.learning.observations.aggregation import (
    BusinessLearningEvidenceLevel,
    BusinessLearningInterpretation,
    BusinessLearningSummary,
)
from app.runtime.learning.observations.trends import (
    BusinessLearningAdvisoryStatus,
    BusinessLearningStabilityLevel,
    BusinessLearningTrendDirection,
    BusinessLearningTrendReport,
)


class BusinessLearningInsightKind(StrEnum):
    POSITIVE_BUSINESS_PATTERN = (
        "positive_business_pattern"
    )
    NEGATIVE_BUSINESS_PATTERN = (
        "negative_business_pattern"
    )


class BusinessLearningCandidateStatus(StrEnum):
    VALIDATED = "validated"
    BLOCKED = "blocked"
    APPROVED = "approved"
    REJECTED = "rejected"


class BusinessLearningApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class BusinessLearningValidationCheck(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    code: str
    passed: bool
    explanation: str


class BusinessLearningCandidateScope(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    tenant_id: str | None = None
    objective_namespace: str
    objective_type: str
    decision: str

    def scope_key(self) -> str:
        return "|".join(
            (
                self.tenant_id or "*",
                self.objective_namespace,
                self.objective_type,
                self.decision,
            )
        )


class BusinessLearningEvidenceSnapshot(BaseModel):
    """
    Immutable source evidence carried by one
    reviewable business-learning candidate.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    historical_summary: BusinessLearningSummary
    recent_summary: BusinessLearningSummary
    trend_report: BusinessLearningTrendReport

    evidence_fingerprint: str = Field(
        min_length=64,
        max_length=64,
    )

    @classmethod
    def from_trend_report(
        cls,
        report: BusinessLearningTrendReport,
    ) -> BusinessLearningEvidenceSnapshot:
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


class BusinessLearningInsightCandidate(BaseModel):
    """
    Human-reviewable proposed business insight.

    Creation, validation, approval, or rejection does
    not alter planning, workflows, routing, policy,
    runtime behavior, or execute business actions.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    candidate_id: UUID = Field(
        default_factory=uuid4
    )
    candidate_version: int = Field(
        default=1,
        ge=1,
    )

    kind: BusinessLearningInsightKind
    scope: BusinessLearningCandidateScope

    statement: str = Field(
        min_length=1
    )
    recommended_review: str = Field(
        min_length=1
    )
    limitations: tuple[str, ...] = ()

    evidence: BusinessLearningEvidenceSnapshot

    validation_checks: tuple[
        BusinessLearningValidationCheck,
        ...,
    ]
    validation_passed: bool

    approval_required: bool = True
    approval_status: (
        BusinessLearningApprovalStatus
    ) = BusinessLearningApprovalStatus.PENDING

    status: BusinessLearningCandidateStatus
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

    @model_validator(mode="after")
    def validate_lifecycle(
        self,
    ) -> BusinessLearningInsightCandidate:
        checks_passed = all(
            check.passed
            for check in self.validation_checks
        )

        if checks_passed != self.validation_passed:
            raise ValueError(
                "validation_passed must match "
                "validation_checks"
            )

        if (
            self.status
            == BusinessLearningCandidateStatus
            .VALIDATED
            and not self.validation_passed
        ):
            raise ValueError(
                "validated candidate must pass "
                "all validation checks"
            )

        if (
            self.status
            == BusinessLearningCandidateStatus
            .BLOCKED
            and self.validation_passed
        ):
            raise ValueError(
                "blocked candidate cannot have "
                "validation_passed"
            )

        if (
            self.status
            == BusinessLearningCandidateStatus
            .APPROVED
            and self.approval_status
            != BusinessLearningApprovalStatus
            .APPROVED
        ):
            raise ValueError(
                "approved candidate requires "
                "approved approval_status"
            )

        if (
            self.status
            == BusinessLearningCandidateStatus
            .REJECTED
            and self.approval_status
            != BusinessLearningApprovalStatus
            .REJECTED
        ):
            raise ValueError(
                "rejected candidate requires "
                "rejected approval_status"
            )

        if self.status in {
            BusinessLearningCandidateStatus.APPROVED,
            BusinessLearningCandidateStatus.REJECTED,
        }:
            if self.reviewed_at is None:
                raise ValueError(
                    "reviewed candidate requires "
                    "reviewed_at"
                )

            if self.reviewed_by_user_id is None:
                raise ValueError(
                    "reviewed candidate requires "
                    "reviewed_by_user_id"
                )

            if not (
                self.review_reason
                and self.review_reason.strip()
            ):
                raise ValueError(
                    "reviewed candidate requires "
                    "review_reason"
                )

        return self


class BusinessLearningInsightPolicy:
    """
    Safety policy for proposing reviewable business
    insight candidates.
    """

    def __init__(
        self,
        *,
        minimum_summary_confidence: float = 0.80,
        maximum_contradiction_score: float = 0.20,
        require_high_evidence: bool = True,
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
        self.require_high_evidence = bool(
            require_high_evidence
        )
        self.require_stable_trend = bool(
            require_stable_trend
        )
        self.approval_required = bool(
            approval_required
        )


class BusinessLearningInsightCandidateFactory:
    def __init__(
        self,
        *,
        policy: (
            BusinessLearningInsightPolicy
            | None
        ) = None,
    ) -> None:
        self.policy = (
            policy
            or BusinessLearningInsightPolicy()
        )

    def propose(
        self,
        *,
        report: BusinessLearningTrendReport,
        proposed_at: datetime | None = None,
    ) -> BusinessLearningInsightCandidate:
        recent = report.recent

        scope = BusinessLearningCandidateScope(
            tenant_id=report.tenant_id,
            objective_namespace=(
                report.objective_namespace
            ),
            objective_type=report.objective_type,
            decision=report.decision,
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

        resolved_at = _aware(
            proposed_at
        )

        if validation_passed:
            status = (
                BusinessLearningCandidateStatus
                .VALIDATED
            )
            validated_at = resolved_at
        else:
            status = (
                BusinessLearningCandidateStatus
                .BLOCKED
            )
            validated_at = None

        if (
            validation_passed
            and self.policy.approval_required
        ):
            blocking_reasons = (
                *blocking_reasons,
                "explicit_approval_required",
            )

        return BusinessLearningInsightCandidate(
            kind=kind,
            scope=scope,
            statement=_statement(
                kind=kind,
                scope=scope,
                recent=recent,
            ),
            recommended_review=(
                _recommended_review(
                    kind=kind,
                    scope=scope,
                )
            ),
            limitations=_limitations(
                report=report
            ),
            evidence=(
                BusinessLearningEvidenceSnapshot
                .from_trend_report(report)
            ),
            validation_checks=checks,
            validation_passed=(
                validation_passed
            ),
            approval_required=(
                self.policy.approval_required
            ),
            approval_status=(
                BusinessLearningApprovalStatus
                .PENDING
            ),
            status=status,
            blocking_reasons=blocking_reasons,
            proposed_at=resolved_at,
            validated_at=validated_at,
        )

    def review(
        self,
        *,
        candidate: BusinessLearningInsightCandidate,
        approved: bool,
        reviewed_by_user_id: UUID,
        reason: str,
        reviewed_at: datetime | None = None,
    ) -> BusinessLearningInsightCandidate:
        if (
            candidate.status
            != BusinessLearningCandidateStatus
            .VALIDATED
            or candidate.approval_status
            != BusinessLearningApprovalStatus
            .PENDING
        ):
            raise ValueError(
                "Only a pending validated business "
                "candidate can be reviewed"
            )

        normalized_reason = reason.strip()

        if not normalized_reason:
            raise ValueError(
                "review reason must not be empty"
            )

        resolved_at = _aware(
            reviewed_at
        )

        if approved:
            status = (
                BusinessLearningCandidateStatus
                .APPROVED
            )
            approval_status = (
                BusinessLearningApprovalStatus
                .APPROVED
            )
            blocking_reasons: tuple[str, ...] = ()
        else:
            status = (
                BusinessLearningCandidateStatus
                .REJECTED
            )
            approval_status = (
                BusinessLearningApprovalStatus
                .REJECTED
            )
            blocking_reasons = (
                "approval_rejected",
            )

        return candidate.model_copy(
            update={
                "candidate_version": (
                    candidate.candidate_version + 1
                ),
                "approval_status": approval_status,
                "status": status,
                "blocking_reasons": (
                    blocking_reasons
                ),
                "reviewed_at": resolved_at,
                "reviewed_by_user_id": (
                    reviewed_by_user_id
                ),
                "review_reason": (
                    normalized_reason
                ),
            }
        )

    def _validation_checks(
        self,
        *,
        report: BusinessLearningTrendReport,
        kind: BusinessLearningInsightKind,
    ) -> tuple[
        BusinessLearningValidationCheck,
        ...,
    ]:
        recent = report.recent

        return (
            _check(
                code=(
                    "comparison_evidence_sufficient"
                ),
                passed=(
                    report
                    .comparison_evidence_sufficient
                ),
                explanation=(
                    "Both historical and recent "
                    "windows must contain sufficient "
                    "business evidence."
                ),
            ),
            _check(
                code="advisory_status_trusted",
                passed=(
                    report.advisory_status
                    == BusinessLearningAdvisoryStatus
                    .TRUST
                ),
                explanation=(
                    "Trend analysis must classify "
                    "the business evidence as trusted."
                ),
            ),
            _check(
                code="stable_business_pattern",
                passed=(
                    not self.policy
                    .require_stable_trend
                    or (
                        report.stability_level
                        == BusinessLearningStabilityLevel
                        .STABLE
                        and report.trend_direction
                        == BusinessLearningTrendDirection
                        .STABLE
                    )
                ),
                explanation=(
                    "A candidate requires a stable, "
                    "non-moving business pattern."
                ),
            ),
            _check(
                code=(
                    "contradiction_within_limit"
                ),
                passed=(
                    report.contradiction_score
                    <= self.policy
                    .maximum_contradiction_score
                ),
                explanation=(
                    "Contradiction must remain within "
                    "the configured safety limit."
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
                    "Recent business evidence must "
                    "meet the confidence threshold."
                ),
            ),
            _check(
                code="recent_evidence_level",
                passed=(
                    not self.policy
                    .require_high_evidence
                    or recent.evidence_level
                    == BusinessLearningEvidenceLevel
                    .HIGH
                ),
                explanation=(
                    "Recent business evidence must "
                    "have a high evidence level."
                ),
            ),
            _check(
                code="supported_interpretation",
                passed=(
                    kind
                    in {
                        BusinessLearningInsightKind
                        .POSITIVE_BUSINESS_PATTERN,
                        BusinessLearningInsightKind
                        .NEGATIVE_BUSINESS_PATTERN,
                    }
                ),
                explanation=(
                    "Only stable positive or negative "
                    "business patterns are supported."
                ),
            ),
        )


def _kind_for_interpretation(
    interpretation: BusinessLearningInterpretation,
) -> BusinessLearningInsightKind:
    if (
        interpretation
        == BusinessLearningInterpretation.POSITIVE
    ):
        return (
            BusinessLearningInsightKind
            .POSITIVE_BUSINESS_PATTERN
        )

    if (
        interpretation
        == BusinessLearningInterpretation.NEGATIVE
    ):
        return (
            BusinessLearningInsightKind
            .NEGATIVE_BUSINESS_PATTERN
        )

    raise ValueError(
        "Only positive or negative stable business "
        "interpretations can produce an insight "
        "candidate"
    )


def _check(
    *,
    code: str,
    passed: bool,
    explanation: str,
) -> BusinessLearningValidationCheck:
    return BusinessLearningValidationCheck(
        code=code,
        passed=bool(passed),
        explanation=explanation,
    )


def _statement(
    *,
    kind: BusinessLearningInsightKind,
    scope: BusinessLearningCandidateScope,
    recent: BusinessLearningSummary,
) -> str:
    pattern = (
        "reliably achieves the business objective"
        if kind
        == BusinessLearningInsightKind
        .POSITIVE_BUSINESS_PATTERN
        else
        "reliably fails to achieve the business "
        "objective"
    )

    return (
        f"Scope `{scope.scope_key()}` {pattern} "
        f"with estimated success rate "
        f"{recent.estimated_success_rate:.3f}, "
        f"failure rate "
        f"{recent.estimated_failure_rate:.3f}, "
        f"and confidence "
        f"{recent.summary_confidence:.3f}."
    )


def _recommended_review(
    *,
    kind: BusinessLearningInsightKind,
    scope: BusinessLearningCandidateScope,
) -> str:
    if (
        kind
        == BusinessLearningInsightKind
        .POSITIVE_BUSINESS_PATTERN
    ):
        return (
            "Review whether this successful pattern "
            "should be documented for operators in "
            f"scope `{scope.scope_key()}`."
        )

    return (
        "Review the failed pattern, its evidence, "
        "and possible process weaknesses for scope "
        f"`{scope.scope_key()}`."
    )


def _limitations(
    *,
    report: BusinessLearningTrendReport,
) -> tuple[str, ...]:
    return (
        "Evidence applies only to the exact "
        "business-objective scope.",
        "Evidence applies only to the two captured "
        "time windows.",
        "Approval records human acceptance only and "
        "does not activate behavior.",
        "The candidate must not directly change "
        "planning, workflows, routing, or policy.",
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
    "BusinessLearningApprovalStatus",
    "BusinessLearningCandidateScope",
    "BusinessLearningCandidateStatus",
    "BusinessLearningEvidenceSnapshot",
    "BusinessLearningInsightCandidate",
    "BusinessLearningInsightCandidateFactory",
    "BusinessLearningInsightKind",
    "BusinessLearningInsightPolicy",
    "BusinessLearningValidationCheck",
]
