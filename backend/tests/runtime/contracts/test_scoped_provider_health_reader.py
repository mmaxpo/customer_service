from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.capabilities.execution.health.decisions import (
    ProviderHealthState,
)
from app.runtime.capabilities.execution.health.reader import (
    DatabaseProviderHealthReader,
    NullProviderHealthReader,
)
from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
)


@pytest.mark.asyncio
async def test_null_reader_returns_unknown_healthy_snapshot():
    snapshot = await NullProviderHealthReader(
    ).get_effective_health(
        user_id=None,
        tenant_id=None,
        capability_id="ecommerce.orders.get",
        provider_id="shopify",
        provider_ref="shopify.get_order",
    )

    assert snapshot.found is False
    assert snapshot.current_state == "healthy"
    assert snapshot.effective_state == "healthy"


@pytest.mark.asyncio
async def test_database_reader_returns_scoped_active_override():
    user_id = uuid4()

    async with SessionLocal() as db:
        await CapabilityProviderHealthRepository(
            db
        ).set_manual_override(
            user_id=user_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            override_state=ProviderHealthState.UNHEALTHY,
            reason="maintenance",
            override_until=(
                datetime.now(timezone.utc)
                + timedelta(hours=1)
            ),
        )

        snapshot = await DatabaseProviderHealthReader(
            db
        ).get_effective_health(
            user_id=str(user_id),
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

    assert snapshot.found is True
    assert snapshot.current_state == "healthy"
    assert snapshot.effective_state == "unhealthy"
    assert snapshot.override_active is True


@pytest.mark.asyncio
async def test_database_reader_is_user_scoped():
    owner_id = uuid4()
    other_id = uuid4()

    async with SessionLocal() as db:
        await CapabilityProviderHealthRepository(
            db
        ).set_manual_override(
            user_id=owner_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            override_state=ProviderHealthState.UNHEALTHY,
            reason="maintenance",
            override_until=None,
        )

        snapshot = await DatabaseProviderHealthReader(
            db
        ).get_effective_health(
            user_id=str(other_id),
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

    assert snapshot.found is False
    assert snapshot.effective_state == "healthy"


@pytest.mark.asyncio
async def test_database_reader_invalid_user_is_safe_unknown():
    async with SessionLocal() as db:
        snapshot = await DatabaseProviderHealthReader(
            db
        ).get_effective_health(
            user_id="not-a-uuid",
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

    assert snapshot.found is False
    assert snapshot.effective_state == "healthy"
