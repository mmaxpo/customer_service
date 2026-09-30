from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.execution import (
    CapabilityExecutorRegistry,
    ProviderHealthEnforcementMode,
    ProviderHealthProbeClaim,
    ProviderHealthSnapshot,
)
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.registry import (
    build_default_system,
)


class UnhealthyReader:
    def __init__(
        self,
        *,
        override_active=False,
    ):
        self.override_active = override_active
        self.calls = 0

    async def get_effective_health(self, **kwargs):
        self.calls += 1

        return ProviderHealthSnapshot(
            found=True,
            user_id=kwargs.get("user_id"),
            tenant_id=kwargs.get("tenant_id"),
            capability_id=kwargs["capability_id"],
            provider_id=kwargs["provider_id"],
            provider_ref=kwargs["provider_ref"],
            current_state="unhealthy",
            effective_state="unhealthy",
            override_active=self.override_active,
            manual_override_state=(
                "unhealthy"
                if self.override_active
                else None
            ),
            observed_at=datetime.now(timezone.utc),
        )


class FakeProbeCoordinator:
    def __init__(
        self,
        *,
        acquired: bool,
        reason: str | None = None,
    ):
        self.acquired = acquired
        self.reason = reason or (
            "probe_lease_acquired"
            if acquired
            else "probe_lease_active"
        )
        self.calls = []

    async def try_claim_probe(self, **kwargs):
        self.calls.append(kwargs)

        return ProviderHealthProbeClaim(
            acquired=self.acquired,
            reason=self.reason,
            scope_key="test-scope",
            lease_token=(
                "probe-token"
                if self.acquired
                else None
            ),
            lease_until=None,
            claimed_at=datetime.now(timezone.utc),
            current_state="unhealthy",
        )


def build_services(user_id):
    return SimpleNamespace(
        identity=SimpleNamespace(
            user_id=user_id,
            tenant_id="tenant_probe_runtime",
        ),
        business=SimpleNamespace(),
    )


def build_executor_registry():
    registry = CapabilityExecutorRegistry()

    async def get_order_executor(context):
        return {
            "provider": (
                context.resolution
                .selected_provider_id
            ),
            "order_ref": (
                context.invocation.inputs[
                    "order_ref"
                ]
            ),
        }

    async def order_action_executor(context):
        return {"performed": True}

    registry.register(
        "shopify.get_order",
        get_order_executor,
    )
    registry.register(
        "shopify.order_action",
        order_action_executor,
    )
    return registry


@pytest.mark.asyncio
async def test_safe_unhealthy_provider_can_receive_probe():
    user_id = uuid4()
    coordinator = FakeProbeCoordinator(
        acquired=True
    )

    resolver = CapabilityResolver(
        services=build_services(user_id),
        system=build_default_system(),
        executor_registry=(
            build_executor_registry()
        ),
        provider_health_reader=UnhealthyReader(),
        provider_health_probe_coordinator=(
            coordinator
        ),
        provider_health_mode=(
            ProviderHealthEnforcementMode
            .ENFORCE_UNHEALTHY
        ),
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
            user_id=user_id,
        )
    )

    assert result.ok is True
    assert len(coordinator.calls) == 1

    attempt = result.metadata[
        "execution_attempts"
    ][0]

    assert attempt["health_probe"] is True
    assert (
        attempt["health_probe_lease_token"]
        == "probe-token"
    )

    health = (
        result.metadata["resolution"]
        ["metadata"]["provider_health"]
    )
    assert (
        health["enforcement_reason"]
        == "controlled_health_probe"
    )


@pytest.mark.asyncio
async def test_active_probe_lease_rejects_provider():
    user_id = uuid4()
    coordinator = FakeProbeCoordinator(
        acquired=False,
        reason="probe_lease_active",
    )

    resolver = CapabilityResolver(
        services=build_services(user_id),
        system=build_default_system(),
        executor_registry=(
            build_executor_registry()
        ),
        provider_health_reader=UnhealthyReader(),
        provider_health_probe_coordinator=(
            coordinator
        ),
        provider_health_mode=(
            ProviderHealthEnforcementMode
            .ENFORCE_UNHEALTHY
        ),
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
            user_id=user_id,
        )
    )

    assert result.ok is False
    assert len(coordinator.calls) >= 1
    assert (
        result.error_code
        == "no_capability_provider_available"
    )


@pytest.mark.asyncio
async def test_unsafe_capability_never_requests_probe():
    user_id = uuid4()
    coordinator = FakeProbeCoordinator(
        acquired=True
    )

    resolver = CapabilityResolver(
        services=build_services(user_id),
        system=build_default_system(),
        executor_registry=(
            build_executor_registry()
        ),
        provider_health_reader=UnhealthyReader(),
        provider_health_probe_coordinator=(
            coordinator
        ),
        provider_health_mode=(
            ProviderHealthEnforcementMode
            .ENFORCE_UNHEALTHY
        ),
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.action",
            inputs={
                "action": "cancel",
                "order_ref": "#1001",
                "idempotency_key": "probe-action-test",
            },
            user_id=user_id,
        )
    )

    assert result.ok is False
    assert coordinator.calls == []


@pytest.mark.asyncio
async def test_manual_unhealthy_override_never_requests_probe():
    user_id = uuid4()
    coordinator = FakeProbeCoordinator(
        acquired=True
    )

    resolver = CapabilityResolver(
        services=build_services(user_id),
        system=build_default_system(),
        executor_registry=(
            build_executor_registry()
        ),
        provider_health_reader=UnhealthyReader(
            override_active=True
        ),
        provider_health_probe_coordinator=(
            coordinator
        ),
        provider_health_mode=(
            ProviderHealthEnforcementMode
            .ENFORCE_UNHEALTHY
        ),
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
            user_id=user_id,
        )
    )

    assert result.ok is False
    assert coordinator.calls == []
