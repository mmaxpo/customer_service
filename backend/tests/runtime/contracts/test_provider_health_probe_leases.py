from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.capabilities.execution.health.decisions import (
    ProviderHealthState,
)
from app.runtime.capabilities.execution.health.probes import (
    DatabaseProviderHealthProbeCoordinator,
)
from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
)


async def create_unhealthy_state(
    *,
    db,
    user_id,
    tenant_id,
    now,
):
    repo = CapabilityProviderHealthRepository(db)

    state = await repo.set_manual_override(
        user_id=user_id,
        tenant_id=tenant_id,
        capability_id="ecommerce.orders.get",
        provider_id="shopify",
        provider_ref="shopify.get_order",
        override_state=ProviderHealthState.HEALTHY,
        reason="create probe test scope",
        override_until=now - timedelta(seconds=1),
    )

    state.current_state = "unhealthy"
    state.manual_override_state = None
    state.manual_override_reason = None
    state.manual_override_until = None
    state.cooldown_until = now - timedelta(seconds=1)
    state.probe_lease_token = None
    state.probe_lease_until = None
    state.probe_claimed_at = None

    await db.commit()
    await db.refresh(state)
    return state


@pytest.mark.asyncio
async def test_only_one_active_probe_lease_is_acquired():
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        await create_unhealthy_state(
            db=db,
            user_id=user_id,
            tenant_id="tenant_probe_single",
            now=now,
        )

        coordinator = DatabaseProviderHealthProbeCoordinator(db)

        first = await coordinator.try_claim_probe(
            user_id=str(user_id),
            tenant_id="tenant_probe_single",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            observed_at=now,
            lease_seconds=60,
        )

        second = await coordinator.try_claim_probe(
            user_id=str(user_id),
            tenant_id="tenant_probe_single",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            observed_at=now,
            lease_seconds=60,
        )

    assert first.acquired is True
    assert first.reason == "probe_lease_acquired"
    assert first.lease_token
    assert first.lease_until == (now + timedelta(seconds=60))

    assert second.acquired is False
    assert second.reason == "probe_lease_active"
    assert second.lease_until == first.lease_until


@pytest.mark.asyncio
async def test_expired_probe_lease_can_be_reclaimed():
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        state = await create_unhealthy_state(
            db=db,
            user_id=user_id,
            tenant_id="tenant_probe_expired",
            now=now,
        )

        state.probe_lease_token = "expired-token"
        state.probe_lease_until = now - timedelta(seconds=1)
        state.probe_claimed_at = now - timedelta(minutes=2)
        await db.commit()

        claim = await (DatabaseProviderHealthProbeCoordinator(db)).try_claim_probe(
            user_id=str(user_id),
            tenant_id="tenant_probe_expired",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            observed_at=now,
            lease_seconds=60,
        )

    assert claim.acquired is True
    assert claim.lease_token
    assert claim.lease_token != "expired-token"


@pytest.mark.asyncio
async def test_cooldown_blocks_probe():
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        state = await create_unhealthy_state(
            db=db,
            user_id=user_id,
            tenant_id="tenant_probe_cooldown",
            now=now,
        )

        state.cooldown_until = now + timedelta(minutes=5)
        await db.commit()

        claim = await (DatabaseProviderHealthProbeCoordinator(db)).try_claim_probe(
            user_id=str(user_id),
            tenant_id="tenant_probe_cooldown",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            observed_at=now,
        )

    assert claim.acquired is False
    assert claim.reason == "cooldown_active"
    assert claim.cooldown_until == (now + timedelta(minutes=5))


@pytest.mark.asyncio
async def test_manual_override_blocks_probe():
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        repo = CapabilityProviderHealthRepository(db)

        state = await repo.set_manual_override(
            user_id=user_id,
            tenant_id="tenant_probe_override",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            override_state=ProviderHealthState.UNHEALTHY,
            reason="operator block",
            override_until=now + timedelta(hours=1),
        )

        state.current_state = "unhealthy"
        state.cooldown_until = now - timedelta(seconds=1)
        await db.commit()

        claim = await (DatabaseProviderHealthProbeCoordinator(db)).try_claim_probe(
            user_id=str(user_id),
            tenant_id="tenant_probe_override",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            observed_at=now,
        )

    assert claim.acquired is False
    assert claim.reason == "manual_override_active"
    assert claim.manual_override_active is True


@pytest.mark.asyncio
async def test_non_unhealthy_state_cannot_claim_probe():
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        repo = CapabilityProviderHealthRepository(db)

        state = await repo.set_manual_override(
            user_id=user_id,
            tenant_id="tenant_probe_healthy",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            override_state=ProviderHealthState.HEALTHY,
            reason="create healthy scope",
            override_until=now - timedelta(seconds=1),
        )

        state.current_state = "healthy"
        state.manual_override_state = None
        state.manual_override_reason = None
        state.manual_override_until = None
        state.cooldown_until = None
        await db.commit()

        claim = await (DatabaseProviderHealthProbeCoordinator(db)).try_claim_probe(
            user_id=str(user_id),
            tenant_id="tenant_probe_healthy",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            observed_at=now,
        )

    assert claim.acquired is False
    assert claim.reason == "state_not_restricted"


@pytest.mark.asyncio
async def test_concurrent_sessions_allow_only_one_probe_claim():
    import asyncio

    user_id = uuid4()
    now = datetime.now(timezone.utc)
    tenant_id = "tenant_probe_concurrent"

    async with SessionLocal() as setup_db:
        await create_unhealthy_state(
            db=setup_db,
            user_id=user_id,
            tenant_id=tenant_id,
            now=now,
        )

    async def claim_once():
        async with SessionLocal() as db:
            return await (DatabaseProviderHealthProbeCoordinator(db)).try_claim_probe(
                user_id=str(user_id),
                tenant_id=tenant_id,
                capability_id="ecommerce.orders.get",
                provider_id="shopify",
                provider_ref="shopify.get_order",
                observed_at=now,
                lease_seconds=60,
            )

    first, second = await asyncio.gather(
        claim_once(),
        claim_once(),
    )

    claims = [first, second]
    acquired = [item for item in claims if item.acquired]
    rejected = [item for item in claims if not item.acquired]

    assert len(acquired) == 1
    assert len(rejected) == 1
    assert acquired[0].reason == ("probe_lease_acquired")
    assert rejected[0].reason == ("probe_lease_active")
