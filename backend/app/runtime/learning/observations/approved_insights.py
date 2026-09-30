from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.runtime.learning.observations.aggregation import (
    BusinessLearningEvidenceLevel,
)
from app.runtime.learning.observations.insight_candidates import (
    BusinessLearningApprovalStatus,
    BusinessLearningCandidateStatus,
    BusinessLearningInsightCandidate,
    BusinessLearningInsightKind,
)


class BusinessLearningApprovedInsightScope(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    tenant_id: str | None = None
    objective_namespace: str
    objective_type: str
    decision: str

    def exact_key(
        self,
    ) -> tuple[
        str | None,
        str,
        str,
        str,
    ]:
        return (
            self.tenant_id,
            self.objective_namespace,
            self.objective_type,
            self.decision,
        )


class BusinessLearningApprovedInsightProvenance(
    BaseModel
):
    model_config = ConfigDict(
        extra="forbid"
    )

    candidate_id: UUID
    candidate_version: int = Field(
        ge=1
    )
    evidence_fingerprint: str = Field(
        min_length=64,
        max_length=64,
    )

    approved_at: datetime
    approved_by_user_id: UUID
    review_reason: str = Field(
        min_length=1
    )


class BusinessLearningApprovedInsightEvidence(
    BaseModel
):
    model_config = ConfigDict(
        extra="forbid"
    )

    window_start: datetime
    window_end: datetime

    summary_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )
    estimated_success_rate: float = Field(
        ge=0.0,
        le=1.0,
    )
    estimated_failure_rate: float = Field(
        ge=0.0,
        le=1.0,
    )
    effective_sample_size: float = Field(
        ge=0.0
    )

    evidence_level: BusinessLearningEvidenceLevel

    contradiction_score: float = Field(
        ge=0.0,
        le=1.0,
    )
    stability_score: float = Field(
        ge=0.0,
        le=1.0,
    )


class BusinessLearningApprovedInsight(BaseModel):
    """
    Read-only operator-facing projection of one
    approved business-learning candidate.

    It is descriptive evidence only. It does not
    activate recommendations, alter planning,
    modify workflows or routing, change runtime
    policy, or authorize business actions.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    kind: BusinessLearningInsightKind
    scope: BusinessLearningApprovedInsightScope

    statement: str = Field(
        min_length=1
    )
    recommended_review: str = Field(
        min_length=1
    )
    limitations: tuple[str, ...] = ()

    evidence: BusinessLearningApprovedInsightEvidence
    provenance: BusinessLearningApprovedInsightProvenance

    read_only: bool = True
    operator_review_only: bool = True

    affects_planning: bool = False
    affects_workflows: bool = False
    affects_routing: bool = False
    affects_runtime_policy: bool = False
    authorizes_business_action: bool = False

    @model_validator(mode="after")
    def validate_safety_boundary(
        self,
    ) -> BusinessLearningApprovedInsight:
        if not self.read_only:
            raise ValueError(
                "Approved business insight must "
                "remain read-only"
            )

        if not self.operator_review_only:
            raise ValueError(
                "Approved business insight must "
                "remain operator-review-only"
            )

        forbidden = (
            self.affects_planning,
            self.affects_workflows,
            self.affects_routing,
            self.affects_runtime_policy,
            self.authorizes_business_action,
        )

        if any(forbidden):
            raise ValueError(
                "Approved business insight cannot "
                "alter system behavior or authorize "
                "business actions"
            )

        return self


class BusinessLearningApprovedInsightProjection:
    @staticmethod
    def from_candidate(
        candidate: BusinessLearningInsightCandidate,
    ) -> BusinessLearningApprovedInsight:
        if (
            candidate.status
            != BusinessLearningCandidateStatus
            .APPROVED
        ):
            raise ValueError(
                "Only approved candidates can be "
                "projected as approved insights"
            )

        if (
            candidate.approval_status
            != BusinessLearningApprovalStatus
            .APPROVED
        ):
            raise ValueError(
                "Candidate approval status must be "
                "approved"
            )

        if not candidate.validation_passed:
            raise ValueError(
                "Approved insight requires validated "
                "evidence"
            )

        if candidate.reviewed_at is None:
            raise ValueError(
                "Approved insight requires reviewed_at"
            )

        if candidate.reviewed_by_user_id is None:
            raise ValueError(
                "Approved insight requires reviewer"
            )

        if not (
            candidate.review_reason
            and candidate.review_reason.strip()
        ):
            raise ValueError(
                "Approved insight requires review "
                "reason"
            )

        recent = candidate.evidence.recent_summary
        trend = candidate.evidence.trend_report

        scope = BusinessLearningApprovedInsightScope(
            tenant_id=candidate.scope.tenant_id,
            objective_namespace=(
                candidate.scope.objective_namespace
            ),
            objective_type=(
                candidate.scope.objective_type
            ),
            decision=candidate.scope.decision,
        )

        trend_scope = (
            trend.tenant_id,
            trend.objective_namespace,
            trend.objective_type,
            trend.decision,
        )

        if scope.exact_key() != trend_scope:
            raise ValueError(
                "Candidate scope does not match "
                "trend evidence scope"
            )

        return BusinessLearningApprovedInsight(
            kind=candidate.kind,
            scope=scope,
            statement=candidate.statement,
            recommended_review=(
                candidate.recommended_review
            ),
            limitations=candidate.limitations,
            evidence=(
                BusinessLearningApprovedInsightEvidence(
                    window_start=recent.window_start,
                    window_end=recent.window_end,
                    summary_confidence=(
                        recent.summary_confidence
                    ),
                    estimated_success_rate=(
                        recent.estimated_success_rate
                    ),
                    estimated_failure_rate=(
                        recent.estimated_failure_rate
                    ),
                    effective_sample_size=(
                        recent.effective_sample_size
                    ),
                    evidence_level=(
                        recent.evidence_level
                    ),
                    contradiction_score=(
                        trend.contradiction_score
                    ),
                    stability_score=(
                        trend.stability_score
                    ),
                )
            ),
            provenance=(
                BusinessLearningApprovedInsightProvenance(
                    candidate_id=(
                        candidate.candidate_id
                    ),
                    candidate_version=(
                        candidate.candidate_version
                    ),
                    evidence_fingerprint=(
                        candidate.evidence
                        .evidence_fingerprint
                    ),
                    approved_at=(
                        candidate.reviewed_at
                    ),
                    approved_by_user_id=(
                        candidate
                        .reviewed_by_user_id
                    ),
                    review_reason=(
                        candidate.review_reason
                        .strip()
                    ),
                )
            ),
        )


__all__ = [
    "BusinessLearningApprovedInsight",
    "BusinessLearningApprovedInsightEvidence",
    "BusinessLearningApprovedInsightProjection",
    "BusinessLearningApprovedInsightProvenance",
    "BusinessLearningApprovedInsightScope",
]
