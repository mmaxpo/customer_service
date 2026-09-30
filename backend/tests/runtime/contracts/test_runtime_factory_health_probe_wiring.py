from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.resources import get_runtime_services
from app.runtime.resources import RuntimeServiceFactory
from app.runtime.capabilities.execution import (
    IsolatedDatabaseProviderHealthProbeCoordinator,
)
from app.runtime.capabilities.execution.health.decisions import (
    ProviderHealthState,
)
from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
)


@pytest.mark.asyncio
async def test_factory_wires_database_probe_coordinator():
    async with SessionLocal() as db:
        services = RuntimeServiceFactory.build(
            db=db,
            user_id=uuid4(),
            tenant_id="tenant_factory_probe",
        )

        coordinator = (
            services.capabilities
            .resolver
            .provider_health_probe_coordinator
        )

        assert isinstance(
            coordinator,
            IsolatedDatabaseProviderHealthProbeCoordinator,
        )


@pytest.mark.asyncio
async def test_context_wires_database_probe_coordinator():
    async with SessionLocal() as db:
        services = RuntimeServiceFactory.build(
            db=None,
            user_id=uuid4(),
            tenant_id="tenant_context_probe",
        )
        services.capabilities = None
        services.data.db = db

        resolved = get_runtime_services(
            SimpleNamespace(
                services=services,
                db=db,
            )
        )

        coordinator = (
            resolved.capabilities
            .resolver
            .provider_health_probe_coordinator
        )

        assert isinstance(
            coordinator,
            IsolatedDatabaseProviderHealthProbeCoordinator,
        )



@pytest.mark.asyncio
async def test_factory_probe_coordinator_does_not_commit_business_session():
    user_id = uuid4()
    target_tenant_id = "tenant_factory_probe_isolation_target"
    marker_tenant_id = "tenant_factory_probe_isolation_marker"
    now = datetime.now(timezone.utc)

    async with SessionLocal() as setup_db:
        repo = CapabilityProviderHealthRepository(
            setup_db
        )

        target_state = await repo.set_manual_override(
            user_id=user_id,
            tenant_id=target_tenant_id,
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            override_state=ProviderHealthState.HEALTHY,
            reason="create target scope",
            override_until=(
                now - timedelta(seconds=1)
            ),
        )
        target_state.current_state = "unhealthy"
        target_state.manual_override_state = None
        target_state.manual_override_reason = None
        target_state.manual_override_until = None
        target_state.cooldown_until = (
            now - timedelta(seconds=1)
        )
        target_state.probe_lease_token = None
        target_state.probe_lease_until = None
        target_state.probe_claimed_at = None
        await setup_db.commit()

        marker_state = await repo.set_manual_override(
            user_id=user_id,
            tenant_id=marker_tenant_id,
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            override_state=ProviderHealthState.HEALTHY,
            reason="committed marker baseline",
            override_until=(
                now - timedelta(seconds=1)
            ),
        )
        marker_state.current_state = "healthy"
        marker_state.manual_override_state = None
        marker_state.manual_override_reason = None
        marker_state.manual_override_until = None
        marker_state.cooldown_until = None
        await setup_db.commit()

    async with SessionLocal() as business_db:
        business_repo = (
            CapabilityProviderHealthRepository(
                business_db
            )
        )

        marker_state = await business_repo.get_state(
            user_id=user_id,
            tenant_id=marker_tenant_id,
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )
        assert marker_state is not None

        # Flush unrelated business work on a different row. The health
        # coordinator must neither commit nor roll back this transaction.
        marker_state.manual_override_reason = (
            "uncommitted business mutation"
        )
        await business_db.flush()

        services = RuntimeServiceFactory.build(
            db=business_db,
            user_id=user_id,
            tenant_id=target_tenant_id,
            provider_health_mode="enforce_unhealthy",
        )
        coordinator = (
            services.capabilities
            .resolver
            .provider_health_probe_coordinator
        )

        claim = await coordinator.try_claim_probe(
            user_id=str(user_id),
            tenant_id=target_tenant_id,
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            observed_at=now,
            lease_seconds=60,
        )

        assert claim.acquired is True

        async with SessionLocal() as verify_db:
            verify_repo = (
                CapabilityProviderHealthRepository(
                    verify_db
                )
            )

            visible_target = await verify_repo.get_state(
                user_id=user_id,
                tenant_id=target_tenant_id,
                capability_id="ecommerce.orders.get",
                provider_id="shopify",
                provider_ref="shopify.get_order",
            )
            visible_marker = await verify_repo.get_state(
                user_id=user_id,
                tenant_id=marker_tenant_id,
                capability_id="ecommerce.orders.get",
                provider_id="shopify",
                provider_ref="shopify.get_order",
            )

            assert visible_target is not None
            assert (
                visible_target.probe_lease_token
                == claim.lease_token
            )

            assert visible_marker is not None
            assert (
                visible_marker.manual_override_reason
                is None
            )

        await business_db.rollback()

    async with SessionLocal() as final_db:
        final_repo = CapabilityProviderHealthRepository(
            final_db
        )

        final_target = await final_repo.get_state(
            user_id=user_id,
            tenant_id=target_tenant_id,
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )
        final_marker = await final_repo.get_state(
            user_id=user_id,
            tenant_id=marker_tenant_id,
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

        assert final_target is not None
        assert (
            final_target.probe_lease_token
            == claim.lease_token
        )

        assert final_marker is not None
        assert (
            final_marker.manual_override_reason
            is None
        )
