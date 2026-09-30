from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.domains.customer_service.services.support.learning.customer_support_objective_learning_candidate_generation import (
    CustomerSupportObjectiveLearningCandidateGenerationResult,
)
from app.domains.customer_service.services.support.learning.customer_support_objective_learning_durable_policy_generation import (
    CustomerSupportObjectiveLearningDurablePolicyGenerationService,
    CustomerSupportObjectiveLearningPolicyDisabledError,
    CustomerSupportObjectiveLearningPolicyNotFoundError,
)
from app.domains.customer_service.services.support.learning.objective_learning_profiles import (
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
    CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
    build_customer_support_objective_learning_profile,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningPolicyRepository,
    ObjectiveLearningPolicyScope,
)


class FakeGenerator:
    def __init__(self, *, result) -> None:
        self.result = result
        self.calls = []

    async def generate(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


@pytest.mark.asyncio
async def test_generation_requires_explicit_durable_policy():
    user_id = uuid4()
    tenant_id = f"tenant-durable-generation-{uuid4()}"

    async with SessionLocal() as db:
        service = CustomerSupportObjectiveLearningDurablePolicyGenerationService(db)

        with pytest.raises(
            CustomerSupportObjectiveLearningPolicyNotFoundError,
            match="ensure the current policy before generation",
        ):
            await service.generate(
                user_id=user_id,
                tenant_id=tenant_id,
            )


@pytest.mark.asyncio
async def test_generation_consumes_exact_persisted_profile_snapshot():
    user_id = uuid4()
    tenant_id = f"tenant-durable-generation-{uuid4()}"

    durable_profile = build_customer_support_objective_learning_profile(
        profile_version=4,
        policy_version=1,
        minimum_confidence=0.73,
        minimum_effective_sample_size=6.0,
        minimum_stability_score=0.91,
    )

    scope = ObjectiveLearningPolicyScope(
        user_id=user_id,
        tenant_id=tenant_id,
        objective_namespace=(CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE),
        objective_type=CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
        profile_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF),
        policy_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF),
    )

    async with SessionLocal() as db:
        repository = ObjectiveLearningPolicyRepository(db)

        record = await repository.append_revision(
            scope=scope,
            profile=durable_profile,
            created_by_user_id=user_id,
            reason="HTTP-D4 exact durable profile test",
        )

        await db.commit()
        revision_id = record.id

    captured_profiles = []
    fake_generator = FakeGenerator(
        result=(
            CustomerSupportObjectiveLearningCandidateGenerationResult(
                analyzed_summaries=0,
                created_candidates=0,
                existing_candidates=0,
                items=(),
            )
        )
    )

    def generator_factory(profile):
        captured_profiles.append(profile)
        return fake_generator

    async with SessionLocal() as fresh_db:
        service = CustomerSupportObjectiveLearningDurablePolicyGenerationService(
            fresh_db,
            generator_factory=generator_factory,
        )

        resolved = await service.resolve_revision(
            user_id=user_id,
            tenant_id=tenant_id,
        )

        result = await service.generate(
            user_id=user_id,
            tenant_id=tenant_id,
            window_hours=48,
        )

    assert resolved.id == revision_id
    assert resolved.profile == durable_profile

    assert captured_profiles == [durable_profile]

    qualification = captured_profiles[0].qualification_policy

    assert captured_profiles[0].profile_version == 4
    assert qualification.policy_version == 1
    assert qualification.minimum_confidence == 0.73
    assert qualification.minimum_effective_sample_size == 6.0
    assert qualification.minimum_stability_score == 0.91

    assert result.analyzed_summaries == 0
    assert fake_generator.calls == [
        {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "window_hours": 48,
        }
    ]


@pytest.mark.asyncio
async def test_generation_rejects_disabled_durable_revision():
    user_id = uuid4()
    tenant_id = f"tenant-durable-generation-{uuid4()}"

    scope = ObjectiveLearningPolicyScope(
        user_id=user_id,
        tenant_id=tenant_id,
        objective_namespace=(CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE),
        objective_type=CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
        profile_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF),
        policy_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF),
    )

    async with SessionLocal() as db:
        repository = ObjectiveLearningPolicyRepository(db)

        await repository.append_revision(
            scope=scope,
            profile=(build_customer_support_objective_learning_profile()),
            enabled=False,
        )

        await db.commit()

    async with SessionLocal() as fresh_db:
        service = CustomerSupportObjectiveLearningDurablePolicyGenerationService(
            fresh_db
        )

        with pytest.raises(
            CustomerSupportObjectiveLearningPolicyDisabledError,
            match="is disabled",
        ):
            await service.generate(
                user_id=user_id,
                tenant_id=tenant_id,
            )
