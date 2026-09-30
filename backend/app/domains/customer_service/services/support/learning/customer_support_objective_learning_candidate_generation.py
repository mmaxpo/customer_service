from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.services.support.learning.objective_learning_profiles import (
    build_customer_support_objective_learning_profile,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningAggregationPolicy,
    ObjectiveLearningCandidateFactory,
    ObjectiveLearningCandidateGenerationItem,
    ObjectiveLearningCandidatePolicy,
    ObjectiveLearningCandidateRepository,
    ObjectiveLearningExperienceRepository,
    ObjectiveLearningLifecycleOperations,
    ObjectiveLearningProfile,
    ObjectiveLearningSummaryService,
)


class CustomerSupportObjectiveLearningCandidateGenerationResult(BaseModel):
    """
    Product-owned result for one explicit generation pass.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    analyzed_summaries: int = Field(ge=0)
    created_candidates: int = Field(ge=0)
    existing_candidates: int = Field(ge=0)

    items: tuple[
        ObjectiveLearningCandidateGenerationItem,
        ...,
    ] = ()


class CustomerSupportObjectiveLearningCandidateGenerationService:
    """
    Explicitly generate reviewable customer-support candidates.

    Product composition maps one exact versioned customer-support
    profile into the generic aggregation and candidate policies.

    This service is informational and advisory only. It does not
    publish events, enqueue jobs, schedule itself, activate approved
    insights, alter planning or ranking, select capabilities or
    providers, modify workflow behavior, bypass approval or
    verification, or authorize execution.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        profile: ObjectiveLearningProfile | None = None,
        experience_repository: (ObjectiveLearningExperienceRepository | None) = None,
        candidate_repository: (ObjectiveLearningCandidateRepository | None) = None,
        summary_service: (ObjectiveLearningSummaryService | None) = None,
        lifecycle: (ObjectiveLearningLifecycleOperations | None) = None,
    ) -> None:
        self.db = db
        self.profile = profile or build_customer_support_objective_learning_profile()

        if not self.profile.enabled:
            raise ValueError(
                "customer-support objective-learning profile "
                "must be enabled for candidate generation"
            )

        qualification = self.profile.qualification_policy

        self.aggregation_policy = ObjectiveLearningAggregationPolicy(
            minimum_effective_sample_size=(qualification.minimum_effective_sample_size)
        )

        self.candidate_policy = ObjectiveLearningCandidatePolicy(
            policy_ref=qualification.policy_ref,
            policy_version=qualification.policy_version,
            minimum_summary_confidence=(qualification.minimum_confidence),
            require_sufficient_evidence=True,
            require_dimension_evidence=True,
            explicit_approval_required=(qualification.explicit_approval_required),
            informational_only=(qualification.informational_only),
            affects_ranking=(qualification.affects_ranking),
            affects_capability_selection=(qualification.affects_capability_selection),
            affects_business_plan=(qualification.affects_business_plan),
            selects_provider=(qualification.selects_provider),
            authorizes_execution=(qualification.authorizes_execution),
            bypasses_approval=(qualification.bypasses_approval),
            bypasses_verification=(qualification.bypasses_verification),
        )

        resolved_experience_repository = (
            experience_repository or ObjectiveLearningExperienceRepository(db)
        )

        resolved_candidate_repository = (
            candidate_repository or ObjectiveLearningCandidateRepository(db)
        )

        self.summary_service = summary_service or ObjectiveLearningSummaryService(
            db=db,
            repository=resolved_experience_repository,
            aggregation_policy=self.aggregation_policy,
        )

        self.lifecycle = lifecycle or ObjectiveLearningLifecycleOperations(
            db=db,
            repository=resolved_candidate_repository,
            factory=ObjectiveLearningCandidateFactory(policy=self.candidate_policy),
        )

    async def generate(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None = None,
        window_hours: int = 720,
        now: datetime | None = None,
    ) -> CustomerSupportObjectiveLearningCandidateGenerationResult:
        """
        Summarize exact-profile evidence and propose candidates.

        Repeated calls are idempotent through the generic candidate
        lifecycle's deterministic policy-aware candidate identity.
        """

        summaries = await self.summary_service.summarize(
            user_id=user_id,
            window_hours=window_hours,
            tenant_id=tenant_id,
            objective_namespace=(self.profile.objective_namespace),
            objective_type=self.profile.objective_type,
            profile_ref=self.profile.profile_ref,
            profile_version=self.profile.profile_version,
            now=now,
        )

        items: list[ObjectiveLearningCandidateGenerationItem] = []

        created_candidates = 0
        existing_candidates = 0

        for summary in summaries:
            generated = await self.lifecycle.propose(
                user_id=user_id,
                aggregation=summary,
                proposed_at=now,
            )

            items.append(generated.item)

            if generated.created:
                created_candidates += 1
            else:
                existing_candidates += 1

        return CustomerSupportObjectiveLearningCandidateGenerationResult(
            analyzed_summaries=len(summaries),
            created_candidates=created_candidates,
            existing_candidates=existing_candidates,
            items=tuple(items),
        )


__all__ = [
    "CustomerSupportObjectiveLearningCandidateGenerationResult",
    "CustomerSupportObjectiveLearningCandidateGenerationService",
]
