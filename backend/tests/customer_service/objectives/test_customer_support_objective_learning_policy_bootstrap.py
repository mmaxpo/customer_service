from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.domains.customer_service.services.support.learning.customer_support_objective_learning_policy_bootstrap import (
    CustomerSupportObjectiveLearningPolicyBootstrapService,
)
from app.domains.customer_service.services.support.learning.objective_learning_profiles import (
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_VERSION,
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_VERSION,
    CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
    CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
    build_customer_support_objective_learning_profile,
)
from app.models.models import (
    ObjectiveLearningPolicyRevisionRecord,
)


@pytest.mark.asyncio
async def test_bootstrap_creates_and_reuses_exact_server_policy():
    user_id = uuid4()
    tenant_id = f"tenant-policy-bootstrap-{uuid4()}"

    async with SessionLocal() as db:
        service = CustomerSupportObjectiveLearningPolicyBootstrapService(db)

        first = await service.ensure_current(
            user_id=user_id,
            tenant_id=tenant_id,
            created_by_user_id=user_id,
        )
        repeated = await service.ensure_current(
            user_id=user_id,
            tenant_id=tenant_id,
            created_by_user_id=user_id,
        )

        await db.commit()

        first_id = first.revision.id
        repeated_id = repeated.revision.id

    assert first.created is True
    assert repeated.created is False
    assert first_id == repeated_id

    async with SessionLocal() as fresh_db:
        rows = list(
            (
                await fresh_db.execute(
                    select(ObjectiveLearningPolicyRevisionRecord).where(
                        ObjectiveLearningPolicyRevisionRecord.user_id == user_id,
                        ObjectiveLearningPolicyRevisionRecord.tenant_id == tenant_id,
                    )
                )
            )
            .scalars()
            .all()
        )

    assert len(rows) == 1

    row = rows[0]

    assert row.id == first_id
    assert row.objective_namespace == (CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE)
    assert row.objective_type == (CUSTOMER_SUPPORT_OBJECTIVE_TYPE)
    assert row.profile_ref == (CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF)
    assert row.profile_version == (CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_VERSION)
    assert row.policy_ref == (CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF)
    assert row.policy_version == (CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_VERSION)

    expected_profile = build_customer_support_objective_learning_profile()

    assert row.profile_json == expected_profile.model_dump(mode="json")
    assert row.enabled is True
    assert row.informational_only is True
    assert row.authorizes_execution is False


@pytest.mark.asyncio
async def test_bootstrap_reconstructs_policy_from_fresh_session():
    user_id = uuid4()
    tenant_id = f"tenant-policy-bootstrap-{uuid4()}"

    async with SessionLocal() as db:
        result = await CustomerSupportObjectiveLearningPolicyBootstrapService(
            db
        ).ensure_current(
            user_id=user_id,
            tenant_id=tenant_id,
        )
        await db.commit()
        revision_id = result.revision.id

    async with SessionLocal() as fresh_db:
        repeated = await CustomerSupportObjectiveLearningPolicyBootstrapService(
            fresh_db
        ).ensure_current(
            user_id=user_id,
            tenant_id=tenant_id,
        )

        await fresh_db.commit()

    assert repeated.created is False
    assert repeated.revision.id == revision_id
    assert repeated.revision.profile == (
        build_customer_support_objective_learning_profile()
    )
    assert repeated.revision.informational_only is True
    assert repeated.revision.authorizes_execution is False


@pytest.mark.asyncio
async def test_bootstrap_is_scoped_by_user_and_tenant():
    first_user_id = uuid4()
    second_user_id = uuid4()

    first_tenant = f"tenant-policy-bootstrap-{uuid4()}"
    second_tenant = f"tenant-policy-bootstrap-{uuid4()}"

    async with SessionLocal() as db:
        service = CustomerSupportObjectiveLearningPolicyBootstrapService(db)

        first = await service.ensure_current(
            user_id=first_user_id,
            tenant_id=first_tenant,
        )
        second_user = await service.ensure_current(
            user_id=second_user_id,
            tenant_id=first_tenant,
        )
        second_tenant_result = await service.ensure_current(
            user_id=first_user_id,
            tenant_id=second_tenant,
        )

        await db.commit()

    ids = {
        first.revision.id,
        second_user.revision.id,
        second_tenant_result.revision.id,
    }

    assert len(ids) == 3

    async with SessionLocal() as fresh_db:
        count = await fresh_db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningPolicyRevisionRecord)
            .where(ObjectiveLearningPolicyRevisionRecord.id.in_(ids))
        )

    assert count == 3


@pytest.mark.asyncio
async def test_bootstrap_fails_on_durable_definition_drift():
    user_id = uuid4()
    tenant_id = f"tenant-policy-bootstrap-{uuid4()}"

    async with SessionLocal() as db:
        service = CustomerSupportObjectiveLearningPolicyBootstrapService(db)

        created = await service.ensure_current(
            user_id=user_id,
            tenant_id=tenant_id,
        )
        await db.commit()
        revision_id = created.revision.id

    async with SessionLocal() as db:
        row = await db.get(
            ObjectiveLearningPolicyRevisionRecord,
            revision_id,
        )
        assert row is not None

        drifted = dict(row.profile_json)
        drifted_policy = dict(drifted["qualification_policy"])
        drifted_policy["minimum_confidence"] = 0.25
        drifted["qualification_policy"] = drifted_policy
        row.profile_json = drifted

        await db.commit()

    async with SessionLocal() as fresh_db:
        service = CustomerSupportObjectiveLearningPolicyBootstrapService(fresh_db)

        with pytest.raises(
            ValueError,
            match=("does not match the server-owned definition"),
        ):
            await service.ensure_current(
                user_id=user_id,
                tenant_id=tenant_id,
            )

        await fresh_db.rollback()


@pytest.mark.asyncio
async def test_bootstrap_does_not_commit_caller_transaction():
    user_id = uuid4()
    tenant_id = f"tenant-policy-bootstrap-{uuid4()}"

    async with SessionLocal() as db:
        result = await CustomerSupportObjectiveLearningPolicyBootstrapService(
            db
        ).ensure_current(
            user_id=user_id,
            tenant_id=tenant_id,
        )

        revision_id = result.revision.id
        await db.rollback()

    async with SessionLocal() as fresh_db:
        persisted = await fresh_db.get(
            ObjectiveLearningPolicyRevisionRecord,
            revision_id,
        )

    assert persisted is None
