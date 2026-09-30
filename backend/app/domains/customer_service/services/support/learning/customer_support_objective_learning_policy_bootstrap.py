from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.services.support.learning.objective_learning_profiles import (
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
    CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
    build_customer_support_objective_learning_profile,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningPolicyRepository,
    ObjectiveLearningPolicyRevision,
    ObjectiveLearningPolicyScope,
)


@dataclass(frozen=True, slots=True)
class CustomerSupportObjectiveLearningPolicyBootstrapResult:
    revision: ObjectiveLearningPolicyRevision
    created: bool


class CustomerSupportObjectiveLearningPolicyBootstrapService:
    """
    Compose and durably ensure the server-owned customer-support
    objective-learning policy for one authenticated ownership scope.

    This service flushes persistence through the repository but does not
    commit. Transaction ownership remains with the caller.

    Ensuring a policy is informational only. It does not generate candidates,
    activate insights, mutate runtime policy, select providers, plan work, or
    authorize execution.
    """

    REASON = "server-owned customer-support objective-learning policy"

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: ObjectiveLearningPolicyRepository | None = None,
    ) -> None:
        self.repository = repository or ObjectiveLearningPolicyRepository(db)

    async def ensure_current(
        self,
        *,
        user_id: UUID,
        tenant_id: str | None = None,
        created_by_user_id: UUID | None = None,
    ) -> CustomerSupportObjectiveLearningPolicyBootstrapResult:
        profile = build_customer_support_objective_learning_profile()

        scope = ObjectiveLearningPolicyScope(
            user_id=user_id,
            tenant_id=tenant_id,
            objective_namespace=CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
            objective_type=CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
            profile_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF),
            policy_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF),
        )

        record, created = await self.repository.ensure_revision(
            scope=scope,
            profile=profile,
            enabled=True,
            reason=self.REASON,
            created_by_user_id=created_by_user_id,
        )

        revision = self.repository.deserialize(record)

        return CustomerSupportObjectiveLearningPolicyBootstrapResult(
            revision=revision,
            created=created,
        )


__all__ = [
    "CustomerSupportObjectiveLearningPolicyBootstrapResult",
    "CustomerSupportObjectiveLearningPolicyBootstrapService",
]
