from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.capabilities.execution import (
    CapabilityRuntimePolicyPatch,
    CapabilityRuntimePolicyRepository,
    CapabilityRuntimePolicyScope,
    DatabaseCapabilityRuntimePolicyReader,
    NullCapabilityRuntimePolicyReader,
)


@pytest.mark.asyncio
async def test_null_reader_returns_safe_code_defaults():
    snapshot = await (
        NullCapabilityRuntimePolicyReader()
        .resolve_policy(
            user_id=None,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )
    )

    assert snapshot.found is False
    assert snapshot.resolution_reason == "code_defaults"
    assert (
        snapshot.effective_policy.health_enforcement_mode
        == "shadow"
    )
    assert (
        snapshot.effective_policy.minimum_performance_attempts
        == 10
    )
    assert snapshot.effective_policy.allocation_enabled is True


def test_policy_patch_validates_complete_score_weights():
    with pytest.raises(
        ValueError,
        match="weights must sum to 1.0",
    ):
        CapabilityRuntimePolicyPatch(
            priority_weight=0.5,
            reliability_weight=0.5,
            latency_weight=0.5,
        )


@pytest.mark.asyncio
async def test_repository_appends_immutable_versions():
    user_id = uuid4()
    tenant_id = f"tenant-policy-{uuid4()}"

    async with SessionLocal() as db:
        repo = CapabilityRuntimePolicyRepository(db)
        scope = CapabilityRuntimePolicyScope(
            user_id=user_id,
            tenant_id=tenant_id,
            capability_id="ecommerce.orders.get",
        )

        first = await repo.append_revision(
            scope=scope,
            policy_payload=CapabilityRuntimePolicyPatch(
                minimum_performance_attempts=20,
            ),
            reason="first",
        )
        second = await repo.append_revision(
            scope=scope,
            policy_payload=CapabilityRuntimePolicyPatch(
                minimum_performance_attempts=30,
            ),
            reason="second",
        )

        await db.commit()

    assert first.scope_key == second.scope_key
    assert first.version == 1
    assert second.version == 2
    assert first.id != second.id


@pytest.mark.asyncio
async def test_policy_reader_merges_deterministic_precedence():
    user_id = uuid4()
    tenant_id = f"tenant-policy-{uuid4()}"

    async with SessionLocal() as db:
        repo = CapabilityRuntimePolicyRepository(db)

        await repo.append_revision(
            scope=CapabilityRuntimePolicyScope(
                user_id=user_id,
            ),
            policy_payload=CapabilityRuntimePolicyPatch(
                performance_window_hours=48,
                minimum_performance_attempts=12,
                allocation_enabled=False,
            ),
        )

        await repo.append_revision(
            scope=CapabilityRuntimePolicyScope(
                user_id=user_id,
                tenant_id=tenant_id,
            ),
            policy_payload=CapabilityRuntimePolicyPatch(
                minimum_performance_attempts=20,
                allocation_enabled=True,
            ),
        )

        await repo.append_revision(
            scope=CapabilityRuntimePolicyScope(
                user_id=user_id,
                tenant_id=tenant_id,
                capability_id="ecommerce.orders.get",
            ),
            policy_payload=CapabilityRuntimePolicyPatch(
                competitive_allocation_margin=0.02,
            ),
        )

        await repo.append_revision(
            scope=CapabilityRuntimePolicyScope(
                user_id=user_id,
                tenant_id=tenant_id,
                provider_id="shopify",
            ),
            policy_payload=CapabilityRuntimePolicyPatch(
                health_enforcement_mode="enforce_unhealthy",
            ),
        )

        await repo.append_revision(
            scope=CapabilityRuntimePolicyScope(
                user_id=user_id,
                tenant_id=tenant_id,
                capability_id="ecommerce.orders.get",
                provider_id="shopify",
                provider_ref="shopify.get_order",
            ),
            policy_payload=CapabilityRuntimePolicyPatch(
                health_probe_lease_seconds=15,
            ),
        )

        await db.commit()

        snapshot = await (
            DatabaseCapabilityRuntimePolicyReader(db)
            .resolve_policy(
                user_id=str(user_id),
                tenant_id=tenant_id,
                capability_id="ecommerce.orders.get",
                provider_id="shopify",
                provider_ref="shopify.get_order",
            )
        )

    policy = snapshot.effective_policy

    assert snapshot.found is True
    assert len(snapshot.applied_revisions) == 5
    assert policy.performance_window_hours == 48
    assert policy.minimum_performance_attempts == 20
    assert policy.allocation_enabled is True
    assert (
        policy.competitive_allocation_margin
        == pytest.approx(0.02)
    )
    assert (
        policy.health_enforcement_mode
        == "enforce_unhealthy"
    )
    assert policy.health_probe_lease_seconds == 15


@pytest.mark.asyncio
async def test_latest_revision_wins_within_same_scope():
    user_id = uuid4()
    tenant_id = f"tenant-policy-{uuid4()}"

    async with SessionLocal() as db:
        repo = CapabilityRuntimePolicyRepository(db)
        scope = CapabilityRuntimePolicyScope(
            user_id=user_id,
            tenant_id=tenant_id,
        )

        await repo.append_revision(
            scope=scope,
            policy_payload=CapabilityRuntimePolicyPatch(
                minimum_performance_attempts=15,
            ),
        )
        await repo.append_revision(
            scope=scope,
            policy_payload=CapabilityRuntimePolicyPatch(
                minimum_performance_attempts=25,
            ),
        )

        await db.commit()

        snapshot = await (
            DatabaseCapabilityRuntimePolicyReader(db)
            .resolve_policy(
                user_id=str(user_id),
                tenant_id=tenant_id,
                capability_id="ecommerce.orders.get",
            )
        )

    assert len(snapshot.applied_revisions) == 1
    assert snapshot.applied_revisions[0].version == 2
    assert (
        snapshot.effective_policy.minimum_performance_attempts
        == 25
    )


@pytest.mark.asyncio
async def test_policy_reader_isolates_authenticated_users():
    first_user = uuid4()
    second_user = uuid4()
    tenant_id = f"tenant-policy-{uuid4()}"

    async with SessionLocal() as db:
        repo = CapabilityRuntimePolicyRepository(db)

        await repo.append_revision(
            scope=CapabilityRuntimePolicyScope(
                user_id=first_user,
                tenant_id=tenant_id,
            ),
            policy_payload=CapabilityRuntimePolicyPatch(
                allocation_enabled=False,
            ),
        )
        await db.commit()

        first = await (
            DatabaseCapabilityRuntimePolicyReader(db)
            .resolve_policy(
                user_id=str(first_user),
                tenant_id=tenant_id,
                capability_id="ecommerce.orders.get",
            )
        )
        second = await (
            DatabaseCapabilityRuntimePolicyReader(db)
            .resolve_policy(
                user_id=str(second_user),
                tenant_id=tenant_id,
                capability_id="ecommerce.orders.get",
            )
        )

    assert first.found is True
    assert first.effective_policy.allocation_enabled is False
    assert second.found is False
    assert second.effective_policy.allocation_enabled is True


@pytest.mark.asyncio
async def test_invalid_user_scope_fails_open_to_defaults():
    snapshot = await (
        DatabaseCapabilityRuntimePolicyReader(
            db=object()
        )
        .resolve_policy(
            user_id="not-a-uuid",
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
        )
    )

    assert snapshot.found is False
    assert snapshot.resolution_reason == "code_defaults"
