from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.objectives.learning.aggregation import (
    ObjectiveLearningAggregation,
    ObjectiveLearningDimensionSummary,
    ObjectiveLearningEvidenceSummary,
)
from app.runtime.objectives.learning.lifecycle import (
    ObjectiveLearningApprovalStatus,
    ObjectiveLearningCandidate,
    ObjectiveLearningCandidateStatus,
)
from app.runtime.objectives.learning.lifecycle_repository import (
    ObjectiveLearningCandidateRepository,
)


class ObjectiveLearningApprovedInsightProvenance(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    candidate_id: UUID
    candidate_version: int = Field(ge=1)

    policy_ref: str = Field(min_length=1)
    policy_version: int = Field(ge=1)

    scope_fingerprint: str = Field(
        min_length=64,
        max_length=64,
    )

    proposed_at: datetime
    validated_at: datetime
    reviewed_at: datetime
    reviewed_by_user_id: UUID
    review_reason: str = Field(min_length=1)


class ObjectiveLearningApprovedInsight(BaseModel):
    """
    Safe advisory projection of one approved candidate.

    Approval records acceptance of evidence only. This projection has
    no authority to change planning, ranking, capability selection,
    provider selection, workflow behavior, policy, or execution.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
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

    validity_scope: dict[str, Any]
    dimensions: tuple[
        ObjectiveLearningDimensionSummary,
        ...,
    ]
    evidence: ObjectiveLearningEvidenceSummary

    total_experiences: int = Field(ge=1)
    effective_sample_size: float = Field(ge=0.0)
    minimum_effective_sample_size: float = Field(gt=0.0)
    evidence_sufficient: bool
    summary_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    decision: str = Field(default="approved")
    recommended_review: str = Field(min_length=1)

    provenance: ObjectiveLearningApprovedInsightProvenance

    limitations: tuple[str, ...] = (
        "Evidence applies only to the exact captured validity scope.",
        "Evidence applies only to the aggregated observations and "
        "contract versions recorded in provenance.",
        "Approval records human acceptance of evidence only.",
        "This insight does not activate behavior or alter planning.",
        "This insight does not rank capabilities or select providers.",
        "This insight does not authorize workflow or business actions.",
    )

    informational_only: bool = True
    affects_ranking: bool = False
    affects_capability_selection: bool = False
    affects_business_plan: bool = False
    selects_provider: bool = False
    authorizes_execution: bool = False
    bypasses_approval: bool = False
    bypasses_verification: bool = False

    @model_validator(mode="after")
    def enforce_advisory_boundary(
        self,
    ) -> "ObjectiveLearningApprovedInsight":
        if not self.informational_only:
            raise ValueError(
                "approved objective learning insight must remain informational only"
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
                "approved objective learning insight cannot alter planning or execution"
            )

        if self.decision != "approved":
            raise ValueError(
                "approved objective learning insight decision must be approved"
            )

        return self


class ObjectiveLearningApprovedInsightProjection:
    @staticmethod
    def from_candidate(
        candidate: ObjectiveLearningCandidate,
    ) -> ObjectiveLearningApprovedInsight:
        if candidate.status != ObjectiveLearningCandidateStatus.APPROVED:
            raise ValueError(
                "Only approved objective learning candidates can be projected"
            )

        if candidate.approval_status != ObjectiveLearningApprovalStatus.APPROVED:
            raise ValueError(
                "Objective learning candidate approval status must be approved"
            )

        if not candidate.validation_passed:
            raise ValueError(
                "Approved objective learning insight requires validated evidence"
            )

        if candidate.validated_at is None:
            raise ValueError(
                "Approved objective learning insight requires validated_at"
            )

        if candidate.reviewed_at is None:
            raise ValueError("Approved objective learning insight requires reviewed_at")

        if candidate.reviewed_by_user_id is None:
            raise ValueError(
                "Approved objective learning insight requires reviewed_by_user_id"
            )

        review_reason = (candidate.review_reason or "").strip()

        if not review_reason:
            raise ValueError(
                "Approved objective learning insight requires review_reason"
            )

        if not candidate.informational_only:
            raise ValueError("Approved candidate must remain informational only")

        if any(
            (
                candidate.affects_ranking,
                candidate.affects_capability_selection,
                candidate.affects_business_plan,
                candidate.selects_provider,
                candidate.authorizes_execution,
                candidate.bypasses_approval,
                candidate.bypasses_verification,
            )
        ):
            raise ValueError("Approved candidate cannot alter planning or execution")

        aggregation = ObjectiveLearningAggregation.model_validate(
            candidate.evidence.aggregation_json
        )

        if aggregation.scope_fingerprint != candidate.evidence.scope_fingerprint:
            raise ValueError(
                "Approved candidate aggregation scope "
                "fingerprint does not match provenance"
            )

        if not aggregation.informational_only:
            raise ValueError("Approved aggregation must remain informational only")

        if aggregation.authorizes_execution:
            raise ValueError("Approved aggregation cannot authorize execution")

        return ObjectiveLearningApprovedInsight(
            schema_ref=aggregation.schema_ref,
            profile_ref=aggregation.profile_ref,
            profile_version=aggregation.profile_version,
            extractor_ref=aggregation.extractor_ref,
            extractor_version=aggregation.extractor_version,
            tenant_id=aggregation.tenant_id,
            objective_namespace=(aggregation.objective_namespace),
            objective_type=aggregation.objective_type,
            objective_version=(aggregation.objective_version),
            validity_scope=dict(aggregation.validity_scope),
            dimensions=aggregation.dimensions,
            evidence=aggregation.evidence,
            total_experiences=(aggregation.total_experiences),
            effective_sample_size=(aggregation.effective_sample_size),
            minimum_effective_sample_size=(aggregation.minimum_effective_sample_size),
            evidence_sufficient=(aggregation.evidence_sufficient),
            summary_confidence=(aggregation.summary_confidence),
            recommended_review=review_reason,
            provenance=(
                ObjectiveLearningApprovedInsightProvenance(
                    candidate_id=candidate.candidate_id,
                    candidate_version=(candidate.candidate_version),
                    policy_ref=candidate.policy_ref,
                    policy_version=(candidate.policy_version),
                    scope_fingerprint=(candidate.evidence.scope_fingerprint),
                    proposed_at=candidate.proposed_at,
                    validated_at=candidate.validated_at,
                    reviewed_at=candidate.reviewed_at,
                    reviewed_by_user_id=(candidate.reviewed_by_user_id),
                    review_reason=review_reason,
                )
            ),
        )


class ObjectiveLearningApprovedInsightService:
    """
    Authenticated approved-only objective-learning reads.

    The service returns immutable advisory projections only. It does
    not publish, enqueue, activate, rank, plan, select providers,
    mutate workflow state, or authorize execution.
    """

    def __init__(
        self,
        *,
        db: AsyncSession,
        repository: (ObjectiveLearningCandidateRepository | None) = None,
    ) -> None:
        self.db = db
        self.repository = repository or ObjectiveLearningCandidateRepository(db)

    async def list_approved(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None = None,
        objective_namespace: str | None = None,
        objective_type: str | None = None,
        objective_version: int | None = None,
        schema_ref: str | None = None,
        profile_ref: str | None = None,
        profile_version: int | None = None,
        extractor_ref: str | None = None,
        extractor_version: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ObjectiveLearningApprovedInsight]:
        rows = await self.repository.list_latest_for_user(
            user_id=user_id,
            tenant_id=tenant_id,
            objective_namespace=objective_namespace,
            objective_type=objective_type,
            objective_version=objective_version,
            schema_ref=schema_ref,
            profile_ref=profile_ref,
            profile_version=profile_version,
            extractor_ref=extractor_ref,
            extractor_version=extractor_version,
            status="approved",
            approval_status="approved",
            validation_passed=True,
            limit=limit,
            offset=offset,
        )

        return [
            ObjectiveLearningApprovedInsightProjection.from_candidate(
                self.repository.deserialize(row)
            )
            for row in rows
        ]

    async def get_approved(
        self,
        *,
        user_id: UUID,
        candidate_id: UUID,
    ) -> ObjectiveLearningApprovedInsight | None:
        row = await self.repository.get_latest_for_user(
            user_id=user_id,
            candidate_id=candidate_id,
        )

        if row is None:
            return None

        candidate = self.repository.deserialize(row)

        if (
            candidate.status != ObjectiveLearningCandidateStatus.APPROVED
            or candidate.approval_status != ObjectiveLearningApprovalStatus.APPROVED
            or not candidate.validation_passed
        ):
            return None

        return ObjectiveLearningApprovedInsightProjection.from_candidate(candidate)


__all__ = [
    "ObjectiveLearningApprovedInsight",
    "ObjectiveLearningApprovedInsightProjection",
    "ObjectiveLearningApprovedInsightProvenance",
    "ObjectiveLearningApprovedInsightService",
]
