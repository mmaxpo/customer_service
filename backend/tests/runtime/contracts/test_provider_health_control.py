from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.platform.events.event_store import PlatformEventStore
from app.runtime.capabilities.execution.health.control import (
    CapabilityProviderHealthControlService,
    PROVIDER_HEALTH_OVERRIDE_CLEARED_EVENT,
    PROVIDER_HEALTH_OVERRIDE_SET_EVENT,
)
from app.runtime.capabilities.execution.health.decisions import (
    ProviderHealthState,
)


@pytest.mark.asyncio
async def test_override_is_effective_overlay_not_state_mutation():
    user_id = uuid4()

    async with SessionLocal() as db:
        service = CapabilityProviderHealthControlService(
            db
        )

        result = await service.set_override(
            user_id=user_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            override_state=ProviderHealthState.UNHEALTHY,
            reason="operator maintenance",
            override_until=None,
        )

    assert result["current_state"] == "healthy"
    assert result["effective_state"] == "unhealthy"
    assert result["override_active"] is True


@pytest.mark.asyncio
async def test_clear_override_restores_underlying_effective_state():
    user_id = uuid4()

    async with SessionLocal() as db:
        service = CapabilityProviderHealthControlService(
            db
        )

        await service.set_override(
            user_id=user_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            override_state=ProviderHealthState.UNHEALTHY,
            reason="temporary block",
            override_until=None,
        )

        result = await service.clear_override(
            user_id=user_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

    assert result is not None
    assert result["current_state"] == "healthy"
    assert result["effective_state"] == "healthy"
    assert result["override_active"] is False


@pytest.mark.asyncio
async def test_expired_override_is_not_effective():
    user_id = uuid4()

    async with SessionLocal() as db:
        service = CapabilityProviderHealthControlService(
            db
        )

        state = await service.repo.set_manual_override(
            user_id=user_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            override_state=ProviderHealthState.UNHEALTHY,
            reason="expired",
            override_until=(
                datetime.now(timezone.utc)
                - timedelta(seconds=1)
            ),
        )

        result = service.state_to_dict(state)

    assert result["manual_override_state"] == "unhealthy"
    assert result["override_active"] is False
    assert result["effective_state"] == "healthy"


@pytest.mark.asyncio
async def test_override_rejects_past_expiration():
    user_id = uuid4()

    async with SessionLocal() as db:
        with pytest.raises(
            ValueError,
            match="must be in the future",
        ):
            await CapabilityProviderHealthControlService(
                db
            ).set_override(
                user_id=user_id,
                tenant_id="tenant_1",
                capability_id="ecommerce.orders.get",
                provider_id="shopify",
                provider_ref=None,
                override_state=(
                    ProviderHealthState.DEGRADED
                ),
                reason="invalid expiration",
                override_until=(
                    datetime.now(timezone.utc)
                    - timedelta(minutes=1)
                ),
            )


@pytest.mark.asyncio
async def test_override_actions_publish_immutable_audit_events():
    user_id = uuid4()

    async with SessionLocal() as db:
        service = CapabilityProviderHealthControlService(
            db
        )

        await service.set_override(
            user_id=user_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref=None,
            override_state=ProviderHealthState.DEGRADED,
            reason="operator review",
            override_until=None,
        )

        await service.clear_override(
            user_id=user_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref=None,
        )

        events = await PlatformEventStore(
            db
        ).list_for_user(
            user_id=user_id,
            limit=20,
        )

        set_events = [
            event
            for event in events
            if event.event_type
            == PROVIDER_HEALTH_OVERRIDE_SET_EVENT
        ]
        clear_events = [
            event
            for event in events
            if event.event_type
            == PROVIDER_HEALTH_OVERRIDE_CLEARED_EVENT
        ]

    assert len(set_events) == 1
    assert len(clear_events) == 1
    assert set_events[0].source == (
        "runtime.capabilities.health"
    )
    assert clear_events[0].source == (
        "runtime.capabilities.health"
    )
