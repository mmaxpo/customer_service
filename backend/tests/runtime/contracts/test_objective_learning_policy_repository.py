from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.session import SessionLocal
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


def _scope(*, user_id, tenant_id):
    return ObjectiveLearningPolicyScope(
        user_id=user_id,
        tenant_id=tenant_id,
        objective_namespace=CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
        objective_type=CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
        profile_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF),
        policy_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF),
    )


@pytest.mark.asyncio
async def test_policy_repository_appends_complete_immutable_versions():
    user_id = uuid4()
    tenant_id = f"tenant-policy-{uuid4()}"

    scope = _scope(
        user_id=user_id,
        tenant_id=tenant_id,
    )

    profile_v1 = build_customer_support_objective_learning_profile(
        profile_version=1,
        policy_version=1,
        minimum_confidence=0.96,
        minimum_effective_sample_size=5.0,
    )
    profile_v2 = build_customer_support_objective_learning_profile(
        profile_version=2,
        policy_version=2,
        minimum_confidence=0.88,
        minimum_effective_sample_size=2.0,
    )

    async with SessionLocal() as db:
        repository = ObjectiveLearningPolicyRepository(db)

        first = await repository.append_revision(
            scope=scope,
            profile=profile_v1,
            reason="strict initial policy",
            created_by_user_id=user_id,
        )
        second = await repository.append_revision(
            scope=scope,
            profile=profile_v2,
            reason="reviewed threshold revision",
            created_by_user_id=user_id,
        )

        await db.commit()

        first_id = first.id
        second_id = second.id

    assert first_id != second_id

    async with SessionLocal() as fresh_db:
        repository = ObjectiveLearningPolicyRepository(fresh_db)

        history = await repository.list_revisions(
            scope=scope,
        )
        latest_row = await repository.get_latest_for_scope(
            scope=scope,
        )
        first_row = await repository.get_revision_for_scope(
            scope=scope,
            policy_version=1,
        )

        assert [row.policy_version for row in history] == [2, 1]
        assert latest_row is not None
        assert latest_row.id == second_id
        assert first_row is not None
        assert first_row.id == first_id

        first_revision = repository.deserialize(first_row)
        latest_revision = repository.deserialize(latest_row)

    assert first_revision.policy_version == 1
    assert first_revision.profile_version == 1
    assert first_revision.profile.qualification_policy.minimum_confidence == 0.96
    assert (
        first_revision.profile.qualification_policy.minimum_effective_sample_size == 5.0
    )

    assert latest_revision.policy_version == 2
    assert latest_revision.profile_version == 2
    assert latest_revision.profile.qualification_policy.minimum_confidence == 0.88
    assert (
        latest_revision.profile.qualification_policy.minimum_effective_sample_size
        == 2.0
    )

    for revision in (
        first_revision,
        latest_revision,
    ):
        assert revision.informational_only is True
        assert revision.authorizes_execution is False

        policy = revision.profile.qualification_policy

        assert policy.informational_only is True
        assert policy.affects_ranking is False
        assert policy.affects_capability_selection is False
        assert policy.affects_business_plan is False
        assert policy.selects_provider is False
        assert policy.authorizes_execution is False
        assert policy.bypasses_approval is False
        assert policy.bypasses_verification is False


@pytest.mark.asyncio
async def test_policy_repository_rejects_skipped_versions():
    user_id = uuid4()
    tenant_id = f"tenant-policy-{uuid4()}"

    scope = _scope(
        user_id=user_id,
        tenant_id=tenant_id,
    )

    async with SessionLocal() as db:
        repository = ObjectiveLearningPolicyRepository(db)

        with pytest.raises(
            ValueError,
            match="must be the next append-only revision",
        ):
            await repository.append_revision(
                scope=scope,
                profile=(
                    build_customer_support_objective_learning_profile(
                        profile_version=2,
                        policy_version=2,
                    )
                ),
            )

        await db.rollback()


@pytest.mark.asyncio
async def test_policy_repository_is_scoped_to_authenticated_owner():
    first_user_id = uuid4()
    second_user_id = uuid4()
    tenant_id = f"tenant-policy-{uuid4()}"

    first_scope = _scope(
        user_id=first_user_id,
        tenant_id=tenant_id,
    )
    second_scope = _scope(
        user_id=second_user_id,
        tenant_id=tenant_id,
    )

    async with SessionLocal() as db:
        repository = ObjectiveLearningPolicyRepository(db)

        created = await repository.append_revision(
            scope=first_scope,
            profile=(
                build_customer_support_objective_learning_profile(
                    profile_version=1,
                    policy_version=1,
                )
            ),
        )

        await db.commit()
        created_id = created.id

    async with SessionLocal() as fresh_db:
        repository = ObjectiveLearningPolicyRepository(fresh_db)

        visible = await repository.list_revisions(
            scope=first_scope,
        )
        hidden = await repository.list_revisions(
            scope=second_scope,
        )
        hidden_exact = await repository.get_revision_for_scope(
            scope=second_scope,
            policy_version=1,
        )

    assert [row.id for row in visible] == [created_id]
    assert hidden == []
    assert hidden_exact is None


def test_policy_scope_rejects_profile_identity_mismatch():
    scope = _scope(
        user_id=uuid4(),
        tenant_id=f"tenant-policy-{uuid4()}",
    )

    mismatched = build_customer_support_objective_learning_profile(
        profile_version=1,
        policy_version=1,
    ).model_copy(
        update={
            "profile_ref": "another.product.profile",
        }
    )

    with pytest.raises(
        ValueError,
        match="does not match durable policy scope",
    ):
        scope.validate_profile(mismatched)
