from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.models.models import (
    CapabilityProviderHealthProbeResultRecord,
)
from app.runtime.capabilities.execution.health.decisions import (
    ProviderHealthState,
)
from app.runtime.capabilities.execution.health.probes import (
    DatabaseProviderHealthProbeCoordinator,
)
from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
)


async def create_claimed_probe(
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
        reason="create completion scope",
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

    coordinator = DatabaseProviderHealthProbeCoordinator(db)

    claim = await coordinator.try_claim_probe(
        user_id=str(user_id),
        tenant_id=tenant_id,
        capability_id="ecommerce.orders.get",
        provider_id="shopify",
        provider_ref="shopify.get_order",
        observed_at=now,
        lease_seconds=60,
    )

    assert claim.acquired is True
    return coordinator, claim


@pytest.mark.asyncio
async def test_successful_probe_enters_recovering():
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        coordinator, claim = await create_claimed_probe(
            db=db,
            user_id=user_id,
            tenant_id="tenant_probe_success",
            now=now,
        )

        completed = await coordinator.complete_probe(
            user_id=str(user_id),
            tenant_id="tenant_probe_success",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            lease_token=claim.lease_token,
            succeeded=True,
            completed_at=now + timedelta(seconds=1),
        )

        state = await (CapabilityProviderHealthRepository(db)).get_state(
            user_id=user_id,
            tenant_id="tenant_probe_success",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

    assert completed.completed is True
    assert completed.duplicate is False
    assert completed.reason == "probe_succeeded"
    assert completed.resulting_state == "recovering"
    assert state.current_state == "recovering"
    assert state.cooldown_until is None
    assert state.probe_lease_token is None


@pytest.mark.asyncio
async def test_failed_probe_restarts_cooldown():
    user_id = uuid4()
    now = datetime.now(timezone.utc)
    completed_at = now + timedelta(seconds=1)

    async with SessionLocal() as db:
        coordinator, claim = await create_claimed_probe(
            db=db,
            user_id=user_id,
            tenant_id="tenant_probe_failure",
            now=now,
        )

        completed = await coordinator.complete_probe(
            user_id=str(user_id),
            tenant_id="tenant_probe_failure",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            lease_token=claim.lease_token,
            succeeded=False,
            completed_at=completed_at,
            failure_cooldown_seconds=300,
            failure_kind="timeout",
            error_code="provider_timeout",
        )

        state = await (CapabilityProviderHealthRepository(db)).get_state(
            user_id=user_id,
            tenant_id="tenant_probe_failure",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

    assert completed.completed is True
    assert completed.reason == "probe_failed"
    assert completed.resulting_state == "unhealthy"
    assert state.current_state == "unhealthy"
    assert state.cooldown_until == (completed_at + timedelta(seconds=300))
    assert state.probe_lease_token is None


@pytest.mark.asyncio
async def test_probe_completion_is_idempotent():
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        coordinator, claim = await create_claimed_probe(
            db=db,
            user_id=user_id,
            tenant_id="tenant_probe_duplicate",
            now=now,
        )

        first = await coordinator.complete_probe(
            user_id=str(user_id),
            tenant_id="tenant_probe_duplicate",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            lease_token=claim.lease_token,
            succeeded=True,
            completed_at=now + timedelta(seconds=1),
        )

        second = await coordinator.complete_probe(
            user_id=str(user_id),
            tenant_id="tenant_probe_duplicate",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            lease_token=claim.lease_token,
            succeeded=True,
            completed_at=now + timedelta(seconds=2),
        )

        records = list(
            (
                await db.execute(
                    select(CapabilityProviderHealthProbeResultRecord).where(
                        CapabilityProviderHealthProbeResultRecord.lease_token
                        == claim.lease_token
                    )
                )
            )
            .scalars()
            .all()
        )

    assert first.completed is True
    assert first.duplicate is False
    assert second.completed is True
    assert second.duplicate is True
    assert first.result_id == second.result_id
    assert len(records) == 1


@pytest.mark.asyncio
async def test_wrong_or_expired_token_does_not_mutate():
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        coordinator, claim = await create_claimed_probe(
            db=db,
            user_id=user_id,
            tenant_id="tenant_probe_invalid",
            now=now,
        )

        wrong = await coordinator.complete_probe(
            user_id=str(user_id),
            tenant_id="tenant_probe_invalid",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            lease_token="wrong-token",
            succeeded=True,
            completed_at=now + timedelta(seconds=1),
        )

        expired = await coordinator.complete_probe(
            user_id=str(user_id),
            tenant_id="tenant_probe_invalid",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            lease_token=claim.lease_token,
            succeeded=True,
            completed_at=now + timedelta(minutes=2),
        )

        state = await (CapabilityProviderHealthRepository(db)).get_state(
            user_id=user_id,
            tenant_id="tenant_probe_invalid",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

    assert wrong.completed is False
    assert wrong.reason == "probe_lease_token_mismatch"
    assert expired.completed is False
    assert expired.reason == "probe_lease_expired"
    assert state.current_state == "unhealthy"
    assert state.probe_lease_token == claim.lease_token


@pytest.mark.asyncio
async def test_concurrent_probe_completion_is_idempotent():
    import asyncio

    user_id = uuid4()
    now = datetime.now(timezone.utc)
    tenant_id = "tenant_probe_concurrent_completion"

    async with SessionLocal() as setup_db:
        _, claim = await create_claimed_probe(
            db=setup_db,
            user_id=user_id,
            tenant_id=tenant_id,
            now=now,
        )

    async def complete_once():
        async with SessionLocal() as db:
            return await (DatabaseProviderHealthProbeCoordinator(db)).complete_probe(
                user_id=str(user_id),
                tenant_id=tenant_id,
                capability_id="ecommerce.orders.get",
                provider_id="shopify",
                provider_ref="shopify.get_order",
                lease_token=claim.lease_token,
                succeeded=True,
                completed_at=now + timedelta(seconds=1),
            )

    first, second = await asyncio.gather(
        complete_once(),
        complete_once(),
    )

    results = [first, second]

    assert all(item.completed for item in results)
    assert sum(1 for item in results if item.duplicate) == 1
    assert {item.reason for item in results} == {
        "probe_succeeded",
        "probe_already_completed",
    }

    async with SessionLocal() as verify_db:
        records = list(
            (
                await verify_db.execute(
                    select(CapabilityProviderHealthProbeResultRecord).where(
                        CapabilityProviderHealthProbeResultRecord.lease_token
                        == claim.lease_token
                    )
                )
            )
            .scalars()
            .all()
        )

    assert len(records) == 1


@pytest.mark.asyncio
async def test_recovering_state_uses_one_controlled_lease():
    user_id = uuid4()
    tenant_id = "tenant_recovering_controlled_lease"
    now = datetime.now(timezone.utc)

    async with SessionLocal() as setup_db:
        coordinator, initial_claim = await create_claimed_probe(
            db=setup_db,
            user_id=user_id,
            tenant_id=tenant_id,
            now=now,
        )

        initial_completion = await coordinator.complete_probe(
            user_id=str(user_id),
            tenant_id=tenant_id,
            capability_id=("ecommerce.orders.get"),
            provider_id="shopify",
            provider_ref=("shopify.get_order"),
            lease_token=(initial_claim.lease_token),
            succeeded=True,
            completed_at=(now + timedelta(seconds=1)),
        )

    assert initial_completion.resulting_state == "recovering"

    async with SessionLocal() as first_db:
        first = await DatabaseProviderHealthProbeCoordinator(first_db).try_claim_probe(
            user_id=str(user_id),
            tenant_id=tenant_id,
            capability_id=("ecommerce.orders.get"),
            provider_id="shopify",
            provider_ref=("shopify.get_order"),
            observed_at=(now + timedelta(seconds=2)),
            lease_seconds=60,
        )

    async with SessionLocal() as second_db:
        second = await DatabaseProviderHealthProbeCoordinator(
            second_db
        ).try_claim_probe(
            user_id=str(user_id),
            tenant_id=tenant_id,
            capability_id=("ecommerce.orders.get"),
            provider_id="shopify",
            provider_ref=("shopify.get_order"),
            observed_at=(now + timedelta(seconds=3)),
            lease_seconds=60,
        )

    assert first.acquired is True
    assert first.reason == "recovery_lease_acquired"
    assert first.current_state == "recovering"

    assert second.acquired is False
    assert second.reason == "probe_lease_active"


@pytest.mark.asyncio
async def test_successful_recovery_request_stays_recovering():
    user_id = uuid4()
    tenant_id = "tenant_recovery_success"
    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        coordinator, initial_claim = await create_claimed_probe(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            now=now,
        )

        await coordinator.complete_probe(
            user_id=str(user_id),
            tenant_id=tenant_id,
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            lease_token=initial_claim.lease_token,
            succeeded=True,
            completed_at=(now + timedelta(seconds=1)),
        )

        recovery_claim = await coordinator.try_claim_probe(
            user_id=str(user_id),
            tenant_id=tenant_id,
            capability_id=("ecommerce.orders.get"),
            provider_id="shopify",
            provider_ref=("shopify.get_order"),
            observed_at=(now + timedelta(seconds=2)),
        )

        completed = await coordinator.complete_probe(
            user_id=str(user_id),
            tenant_id=tenant_id,
            capability_id=("ecommerce.orders.get"),
            provider_id="shopify",
            provider_ref=("shopify.get_order"),
            lease_token=(recovery_claim.lease_token),
            succeeded=True,
            completed_at=(now + timedelta(seconds=3)),
        )

    assert completed.completed is True
    assert completed.reason == "recovery_request_succeeded"
    assert completed.previous_state == "recovering"
    assert completed.resulting_state == "recovering"
    assert completed.cooldown_until is None


@pytest.mark.asyncio
async def test_failed_recovery_request_returns_to_unhealthy():
    user_id = uuid4()
    tenant_id = "tenant_recovery_failure"
    now = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        coordinator, initial_claim = await create_claimed_probe(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            now=now,
        )

        await coordinator.complete_probe(
            user_id=str(user_id),
            tenant_id=tenant_id,
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            lease_token=initial_claim.lease_token,
            succeeded=True,
            completed_at=(now + timedelta(seconds=1)),
        )

        recovery_claim = await coordinator.try_claim_probe(
            user_id=str(user_id),
            tenant_id=tenant_id,
            capability_id=("ecommerce.orders.get"),
            provider_id="shopify",
            provider_ref=("shopify.get_order"),
            observed_at=(now + timedelta(seconds=2)),
        )

        completed = await coordinator.complete_probe(
            user_id=str(user_id),
            tenant_id=tenant_id,
            capability_id=("ecommerce.orders.get"),
            provider_id="shopify",
            provider_ref=("shopify.get_order"),
            lease_token=(recovery_claim.lease_token),
            succeeded=False,
            completed_at=(now + timedelta(seconds=3)),
            failure_cooldown_seconds=300,
            failure_kind="timeout",
            error_code="provider_timeout",
        )

    assert completed.completed is True
    assert completed.reason == "recovery_request_failed"
    assert completed.previous_state == "recovering"
    assert completed.resulting_state == "unhealthy"
    assert completed.cooldown_until == (now + timedelta(seconds=303))
