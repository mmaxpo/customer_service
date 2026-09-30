from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.services.support.learning.customer_support_objective_learning_candidate_generation import (
    CustomerSupportObjectiveLearningCandidateGenerationResult,
    CustomerSupportObjectiveLearningCandidateGenerationService,
)
from app.domains.customer_service.services.support.learning.objective_learning_profiles import (
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
    CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningPolicyRepository,
    ObjectiveLearningPolicyRevision,
    ObjectiveLearningPolicyScope,
    ObjectiveLearningProfile,
)


class CustomerSupportObjectiveLearningPolicyNotFoundError(LookupError):
    """No durable customer-support learning policy exists for the scope."""


class CustomerSupportObjectiveLearningPolicyDisabledError(ValueError):
    """The resolved durable policy revision is disabled."""


GeneratorFactory = Callable[
    [ObjectiveLearningProfile],
    CustomerSupportObjectiveLearningCandidateGenerationService,
]


class CustomerSupportObjectiveLearningDurablePolicyGenerationService:
    """
    Resolve the latest exact durable customer-support learning policy
    revision and generate candidates under its persisted profile snapshot.

    This service never bootstraps a missing policy. Policy creation remains
    an explicit authenticated operation through the policy API.

    Durable policy consumption remains informational and advisory only. It
    cannot activate insights, alter planning or ranking, select providers,
    modify workflow behavior, bypass approval or verification, or authorize
    execution.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        policy_repository: (ObjectiveLearningPolicyRepository | None) = None,
        generator_factory: GeneratorFactory | None = None,
    ) -> None:
        self.db = db
        self.policy_repository = policy_repository or ObjectiveLearningPolicyRepository(
            db
        )
        self.generator_factory = generator_factory or self._default_generator_factory

    async def resolve_revision(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None = None,
    ) -> ObjectiveLearningPolicyRevision:
        scope = ObjectiveLearningPolicyScope(
            user_id=user_id,
            tenant_id=tenant_id,
            objective_namespace=(CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE),
            objective_type=CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
            profile_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF),
            policy_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF),
        )

        record = await self.policy_repository.get_latest_for_scope(
            scope=scope,
        )

        if record is None:
            raise CustomerSupportObjectiveLearningPolicyNotFoundError(
                "Durable customer-support objective-learning policy "
                "not found; ensure the current policy before generation"
            )

        revision = self.policy_repository.deserialize(record)

        if not revision.enabled or not revision.profile.enabled:
            raise CustomerSupportObjectiveLearningPolicyDisabledError(
                "Durable customer-support objective-learning policy is disabled"
            )

        return revision

    async def generate(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None = None,
        window_hours: int = 720,
    ) -> CustomerSupportObjectiveLearningCandidateGenerationResult:
        revision = await self.resolve_revision(
            user_id=user_id,
            tenant_id=tenant_id,
        )

        generator = self.generator_factory(revision.profile)

        return await generator.generate(
            user_id=user_id,
            tenant_id=tenant_id,
            window_hours=window_hours,
        )

    def _default_generator_factory(
        self,
        profile: ObjectiveLearningProfile,
    ) -> CustomerSupportObjectiveLearningCandidateGenerationService:
        return CustomerSupportObjectiveLearningCandidateGenerationService(
            self.db,
            profile=profile,
        )


__all__ = [
    "CustomerSupportObjectiveLearningDurablePolicyGenerationService",
    "CustomerSupportObjectiveLearningPolicyDisabledError",
    "CustomerSupportObjectiveLearningPolicyNotFoundError",
]
