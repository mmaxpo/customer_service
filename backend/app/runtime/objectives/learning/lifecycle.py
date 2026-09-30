from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid5

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.runtime.objectives.learning.aggregation import (
    ObjectiveLearningAggregation,
)


_OBJECTIVE_LEARNING_CANDIDATE_NAMESPACE = UUID("7d36d0b9-f183-4c88-b683-dc73622fb4e5")


class ObjectiveLearningCandidateStatus(StrEnum):
    """
    Advisory lifecycle status.

    Approval records operator acceptance only. No status authorizes
    planner, provider, workflow, policy, or execution changes.
    """

    VALIDATED = "validated"
    BLOCKED = "blocked"
    APPROVED = "approved"
    REJECTED = "rejected"


class ObjectiveLearningApprovalStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ObjectiveLearningValidationCheck(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    code: str = Field(min_length=1)
    passed: bool
    explanation: str = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_check(
        self,
    ) -> "ObjectiveLearningValidationCheck":
        object.__setattr__(
            self,
            "code",
            self.code.strip().lower(),
        )
        object.__setattr__(
            self,
            "explanation",
            self.explanation.strip(),
        )

        if not self.code:
            raise ValueError("objective learning validation code is required")

        if not self.explanation:
            raise ValueError("objective learning validation explanation is required")

        return self


class ObjectiveLearningCandidatePolicy(BaseModel):
    """
    Deterministic evidence-to-candidate policy.

    The policy determines whether an advisory candidate may be
    presented for review. It never authorizes use by Planner or runtime.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    policy_ref: str = Field(
        default=("runtime.objective_learning.candidate_policy"),
        min_length=1,
    )
    policy_version: int = Field(
        default=1,
        ge=1,
    )

    minimum_summary_confidence: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
    )
    require_sufficient_evidence: bool = True
    require_dimension_evidence: bool = True
    explicit_approval_required: bool = True

    informational_only: bool = True
    affects_ranking: bool = False
    affects_capability_selection: bool = False
    affects_business_plan: bool = False
    selects_provider: bool = False
    authorizes_execution: bool = False
    bypasses_approval: bool = False
    bypasses_verification: bool = False

    @model_validator(mode="after")
    def validate_policy(
        self,
    ) -> "ObjectiveLearningCandidatePolicy":
        normalized_ref = self.policy_ref.strip().lower()

        if not normalized_ref:
            raise ValueError("objective learning candidate policy_ref is required")

        object.__setattr__(
            self,
            "policy_ref",
            normalized_ref,
        )

        if not self.informational_only:
            raise ValueError(
                "objective learning lifecycle must remain informational only"
            )

        forbidden = (
            self.affects_ranking,
            self.affects_capability_selection,
            self.affects_business_plan,
            self.selects_provider,
            self.authorizes_execution,
            self.bypasses_approval,
            self.bypasses_verification,
        )

        if any(forbidden):
            raise ValueError(
                "objective learning lifecycle policy cannot alter planning or execution"
            )

        return self


class ObjectiveLearningCandidateEvidence(BaseModel):
    """
    Immutable evidence snapshot behind one reviewable candidate.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    scope_fingerprint: str = Field(
        min_length=64,
        max_length=64,
    )

    schema_ref: str = Field(min_length=1)
    profile_ref: str = Field(min_length=1)
    profile_version: int = Field(ge=1)
    extractor_ref: str = Field(min_length=1)
    extractor_version: int = Field(ge=1)

    tenant_id: str | None = None
    objective_namespace: str = Field(min_length=1)
    objective_type: str = Field(min_length=1)
    objective_version: int = Field(ge=1)

    total_experiences: int = Field(ge=1)
    unique_objective_count: int = Field(ge=1)
    unique_resolution_count: int = Field(ge=1)
    effective_sample_size: float = Field(ge=0.0)
    minimum_effective_sample_size: float = Field(gt=0.0)
    summary_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )
    evidence_sufficient: bool

    dimension_keys: tuple[str, ...] = ()
    dimension_count: int = Field(ge=0)

    aggregation_json: dict[str, Any]

    @model_validator(mode="after")
    def validate_evidence(
        self,
    ) -> "ObjectiveLearningCandidateEvidence":
        normalized_keys = tuple(
            sorted(
                {
                    str(value).strip().lower()
                    for value in self.dimension_keys
                    if str(value).strip()
                }
            )
        )

        object.__setattr__(
            self,
            "dimension_keys",
            normalized_keys,
        )

        if self.dimension_count != len(normalized_keys):
            raise ValueError(
                "objective learning candidate "
                "dimension_count does not match "
                "dimension_keys"
            )

        return self

    @classmethod
    def from_aggregation(
        cls,
        aggregation: ObjectiveLearningAggregation,
    ) -> "ObjectiveLearningCandidateEvidence":
        dimension_keys = tuple(
            sorted(dimension.key for dimension in (aggregation.dimensions))
        )

        return cls(
            scope_fingerprint=(aggregation.scope_fingerprint),
            schema_ref=aggregation.schema_ref,
            profile_ref=aggregation.profile_ref,
            profile_version=(aggregation.profile_version),
            extractor_ref=(aggregation.extractor_ref),
            extractor_version=(aggregation.extractor_version),
            tenant_id=aggregation.tenant_id,
            objective_namespace=(aggregation.objective_namespace),
            objective_type=(aggregation.objective_type),
            objective_version=(aggregation.objective_version),
            total_experiences=(aggregation.total_experiences),
            unique_objective_count=(aggregation.unique_objective_count),
            unique_resolution_count=(aggregation.unique_resolution_count),
            effective_sample_size=(aggregation.effective_sample_size),
            minimum_effective_sample_size=(aggregation.minimum_effective_sample_size),
            summary_confidence=(aggregation.summary_confidence),
            evidence_sufficient=(aggregation.evidence_sufficient),
            dimension_keys=dimension_keys,
            dimension_count=len(dimension_keys),
            aggregation_json=(aggregation.model_dump(mode="json")),
        )


class ObjectiveLearningCandidate(BaseModel):
    """
    Immutable reviewable objective-learning candidate revision.

    Approved candidates remain advisory records. They do not affect
    ranking, planning, workflow construction, provider selection,
    runtime policy, approval requirements, or execution.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    candidate_id: UUID
    candidate_version: int = Field(ge=1)

    status: ObjectiveLearningCandidateStatus
    approval_status: ObjectiveLearningApprovalStatus

    policy_ref: str = Field(min_length=1)
    policy_version: int = Field(ge=1)

    evidence: ObjectiveLearningCandidateEvidence

    validation_checks: tuple[
        ObjectiveLearningValidationCheck,
        ...,
    ]
    validation_passed: bool
    approval_required: bool
    blocking_reasons: tuple[str, ...] = ()

    proposed_at: datetime
    validated_at: datetime | None = None

    reviewed_at: datetime | None = None
    reviewed_by_user_id: UUID | None = None
    review_reason: str | None = None

    informational_only: bool = True
    affects_ranking: bool = False
    affects_capability_selection: bool = False
    affects_business_plan: bool = False
    selects_provider: bool = False
    authorizes_execution: bool = False
    bypasses_approval: bool = False
    bypasses_verification: bool = False

    @model_validator(mode="after")
    def validate_candidate(
        self,
    ) -> "ObjectiveLearningCandidate":
        if not self.informational_only:
            raise ValueError(
                "objective learning candidate must remain informational only"
            )

        forbidden = (
            self.affects_ranking,
            self.affects_capability_selection,
            self.affects_business_plan,
            self.selects_provider,
            self.authorizes_execution,
            self.bypasses_approval,
            self.bypasses_verification,
        )

        if any(forbidden):
            raise ValueError(
                "objective learning candidate cannot alter planning or execution"
            )

        expected_validation = all(check.passed for check in self.validation_checks)

        if self.validation_passed != expected_validation:
            raise ValueError(
                "candidate validation_passed does not match validation checks"
            )

        if (
            self.status == ObjectiveLearningCandidateStatus.BLOCKED
            and self.validation_passed
        ):
            raise ValueError("blocked candidate cannot have passing validation")

        if (
            self.status
            in {
                ObjectiveLearningCandidateStatus.VALIDATED,
                ObjectiveLearningCandidateStatus.APPROVED,
                ObjectiveLearningCandidateStatus.REJECTED,
            }
            and not self.validation_passed
        ):
            raise ValueError(
                "validated or reviewed candidate requires passing validation"
            )

        if self.status in {
            ObjectiveLearningCandidateStatus.APPROVED,
            ObjectiveLearningCandidateStatus.REJECTED,
        }:
            if self.candidate_version < 2:
                raise ValueError("reviewed candidate must be a later revision")

            if self.reviewed_at is None:
                raise ValueError("reviewed candidate requires reviewed_at")

            if self.reviewed_by_user_id is None:
                raise ValueError("reviewed candidate requires reviewer")

            if not (self.review_reason and self.review_reason.strip()):
                raise ValueError("reviewed candidate requires review reason")

        normalized_reasons = tuple(
            value
            for value in (str(item).strip().lower() for item in self.blocking_reasons)
            if value
        )

        if len(normalized_reasons) != len(set(normalized_reasons)):
            raise ValueError("candidate blocking reasons must be unique")

        object.__setattr__(
            self,
            "blocking_reasons",
            normalized_reasons,
        )

        return self


class ObjectiveLearningCandidateFactory:
    """
    Pure deterministic lifecycle transition factory.
    """

    def __init__(
        self,
        *,
        policy: (ObjectiveLearningCandidatePolicy | None) = None,
    ) -> None:
        self.policy = policy or ObjectiveLearningCandidatePolicy()

    def propose(
        self,
        *,
        aggregation: ObjectiveLearningAggregation,
        proposed_at: datetime | None = None,
    ) -> ObjectiveLearningCandidate:
        resolved_at = _aware(proposed_at)
        evidence = ObjectiveLearningCandidateEvidence.from_aggregation(aggregation)

        checks = self._validation_checks(aggregation=aggregation)
        validation_passed = all(check.passed for check in checks)

        if validation_passed:
            status = ObjectiveLearningCandidateStatus.VALIDATED
            validated_at = resolved_at
        else:
            status = ObjectiveLearningCandidateStatus.BLOCKED
            validated_at = None

        if validation_passed and self.policy.explicit_approval_required:
            approval_status = ObjectiveLearningApprovalStatus.PENDING
            blocking_reasons = ("explicit_approval_required",)
        elif validation_passed:
            approval_status = ObjectiveLearningApprovalStatus.NOT_REQUIRED
            blocking_reasons = ()
        else:
            approval_status = ObjectiveLearningApprovalStatus.NOT_REQUIRED
            blocking_reasons = tuple(check.code for check in checks if not check.passed)

        candidate_id = uuid5(
            _OBJECTIVE_LEARNING_CANDIDATE_NAMESPACE,
            (
                f"{evidence.scope_fingerprint}:"
                f"{self.policy.policy_ref}:"
                f"{self.policy.policy_version}"
            ),
        )

        return ObjectiveLearningCandidate(
            candidate_id=candidate_id,
            candidate_version=1,
            status=status,
            approval_status=approval_status,
            policy_ref=self.policy.policy_ref,
            policy_version=(self.policy.policy_version),
            evidence=evidence,
            validation_checks=checks,
            validation_passed=validation_passed,
            approval_required=(self.policy.explicit_approval_required),
            blocking_reasons=blocking_reasons,
            proposed_at=resolved_at,
            validated_at=validated_at,
        )

    def review(
        self,
        *,
        candidate: ObjectiveLearningCandidate,
        approved: bool,
        reviewed_by_user_id: UUID,
        reason: str,
        reviewed_at: datetime | None = None,
    ) -> ObjectiveLearningCandidate:
        if (
            candidate.status != ObjectiveLearningCandidateStatus.VALIDATED
            or candidate.approval_status != ObjectiveLearningApprovalStatus.PENDING
        ):
            raise ValueError(
                "Only a pending validated objective learning candidate can be reviewed"
            )

        normalized_reason = reason.strip()

        if not normalized_reason:
            raise ValueError("objective learning review reason must not be empty")

        resolved_at = _aware(reviewed_at)

        if approved:
            status = ObjectiveLearningCandidateStatus.APPROVED
            approval_status = ObjectiveLearningApprovalStatus.APPROVED
            blocking_reasons: tuple[str, ...] = ()
        else:
            status = ObjectiveLearningCandidateStatus.REJECTED
            approval_status = ObjectiveLearningApprovalStatus.REJECTED
            blocking_reasons = ("approval_rejected",)

        return candidate.model_copy(
            update={
                "candidate_version": (candidate.candidate_version + 1),
                "status": status,
                "approval_status": (approval_status),
                "blocking_reasons": (blocking_reasons),
                "reviewed_at": resolved_at,
                "reviewed_by_user_id": (reviewed_by_user_id),
                "review_reason": (normalized_reason),
            }
        )

    def _validation_checks(
        self,
        *,
        aggregation: ObjectiveLearningAggregation,
    ) -> tuple[
        ObjectiveLearningValidationCheck,
        ...,
    ]:
        return (
            ObjectiveLearningValidationCheck(
                code="evidence_sufficient",
                passed=(
                    not self.policy.require_sufficient_evidence
                    or aggregation.evidence_sufficient
                ),
                explanation=(
                    "Aggregated evidence must meet "
                    "the configured effective sample "
                    "size requirement."
                ),
            ),
            ObjectiveLearningValidationCheck(
                code="summary_confidence",
                passed=(
                    aggregation.summary_confidence
                    >= self.policy.minimum_summary_confidence
                ),
                explanation=(
                    "Aggregate summary confidence "
                    "must meet the configured "
                    "candidate threshold."
                ),
            ),
            ObjectiveLearningValidationCheck(
                code="dimension_evidence_present",
                passed=(
                    not self.policy.require_dimension_evidence
                    or bool(aggregation.dimensions)
                ),
                explanation=(
                    "At least one aggregated learning dimension must be present."
                ),
            ),
            ObjectiveLearningValidationCheck(
                code="informational_boundary",
                passed=(
                    aggregation.informational_only
                    and not (aggregation.authorizes_execution)
                ),
                explanation=(
                    "Aggregate evidence must remain "
                    "informational and must not "
                    "authorize execution."
                ),
            ),
        )


def _aware(
    value: datetime | None,
) -> datetime:
    resolved = value or datetime.now(timezone.utc)

    if resolved.tzinfo is None:
        return resolved.replace(tzinfo=timezone.utc)

    return resolved


__all__ = [
    "ObjectiveLearningApprovalStatus",
    "ObjectiveLearningCandidate",
    "ObjectiveLearningCandidateEvidence",
    "ObjectiveLearningCandidateFactory",
    "ObjectiveLearningCandidatePolicy",
    "ObjectiveLearningCandidateStatus",
    "ObjectiveLearningValidationCheck",
]
