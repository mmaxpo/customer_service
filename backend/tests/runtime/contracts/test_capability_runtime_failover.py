from types import SimpleNamespace

import pytest

from app.integrations.errors import (
    IntegrationProviderError,
    IntegrationTimeoutError,
)
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.execution import (
    CapabilityExecutorRegistry,
)
from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.registry import (
    build_default_system,
)


def build_services():
    return SimpleNamespace(
        identity=SimpleNamespace(
            user_id="user_1",
            tenant_id=None,
        ),
        business=SimpleNamespace(),
    )


@pytest.mark.asyncio
async def test_safe_read_falls_back_after_provider_timeout():
    system = build_default_system(
        include_mock_provider=True,
    )
    executors = CapabilityExecutorRegistry()
    calls = []

    async def shopify_executor(context):
        calls.append("shopify")
        raise IntegrationTimeoutError(
            "shopify.get_order timed out"
        )

    async def mock_executor(context):
        calls.append("mock")
        return {
            "source": "mock",
            "order_ref": context.invocation.inputs["order_ref"],
        }

    executors.register(
        "shopify.get_order",
        shopify_executor,
    )
    executors.register(
        "mock.get_order",
        mock_executor,
    )

    resolver = CapabilityResolver(
        services=build_services(),
        system=system,
        executor_registry=executors,
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.output == {
        "source": "mock",
        "order_ref": "#1001",
    }
    assert calls == ["shopify", "mock"]

    assert result.metadata["selected_provider_id"] == "mock"
    assert result.metadata["provider_ref"] == "mock.get_order"
    assert result.metadata["fallback_used"] is True

    attempts = result.metadata["execution_attempts"]

    assert len(attempts) == 2
    assert attempts[0]["provider_id"] == "shopify"
    assert attempts[0]["outcome"] == "error"
    assert attempts[0]["error_code"] == (
        "capability_provider_timeout"
    )
    assert attempts[0]["fallback_allowed"] is True

    assert attempts[1]["provider_id"] == "mock"
    assert attempts[1]["outcome"] == "success"


@pytest.mark.asyncio
async def test_transient_failure_without_alternative_returns_stable_error():
    system = build_default_system()
    executors = CapabilityExecutorRegistry()

    async def shopify_executor(context):
        raise IntegrationTimeoutError(
            "shopify.get_order timed out"
        )

    executors.register(
        "shopify.get_order",
        shopify_executor,
    )
    executors.register(
        "shopify.order_action",
        shopify_executor,
    )

    resolver = CapabilityResolver(
        services=build_services(),
        system=system,
        executor_registry=executors,
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is False
    assert result.error_code == "capability_provider_timeout"
    assert result.metadata["fallback_used"] is False
    assert len(result.metadata["execution_attempts"]) == 1
    assert (
        result.metadata["execution_attempts"][0]["fallback_allowed"]
        is True
    )
    assert (
        result.metadata["fallback_resolution"]["metadata"]
        ["diagnostics"]["status"]
        == "no_enabled_binding"
    )


@pytest.mark.asyncio
async def test_generic_provider_error_does_not_trigger_fallback():
    system = build_default_system(
        include_mock_provider=True,
    )
    executors = CapabilityExecutorRegistry()
    calls = []

    async def shopify_executor(context):
        calls.append("shopify")
        raise IntegrationProviderError(
            "wrapped provider failure"
        )

    async def mock_executor(context):
        calls.append("mock")
        return {"source": "mock"}

    executors.register(
        "shopify.get_order",
        shopify_executor,
    )
    executors.register(
        "mock.get_order",
        mock_executor,
    )

    resolver = CapabilityResolver(
        services=build_services(),
        system=system,
        executor_registry=executors,
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is False
    assert result.error_code == "capability_provider_error"
    assert calls == ["shopify"]
    assert result.metadata["fallback_used"] is False
    assert (
        result.metadata["execution_attempts"][0]["fallback_allowed"]
        is False
    )


@pytest.mark.asyncio
async def test_high_risk_action_never_falls_back_after_timeout():
    system = build_default_system()
    executors = CapabilityExecutorRegistry()
    calls = []

    async def action_executor(context):
        calls.append("shopify")
        raise IntegrationTimeoutError(
            "shopify.order_action timed out"
        )

    executors.register(
        "shopify.get_order",
        action_executor,
    )
    executors.register(
        "shopify.order_action",
        action_executor,
    )

    resolver = CapabilityResolver(
        services=build_services(),
        system=system,
        executor_registry=executors,
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.action",
            inputs={
                "action": "cancel",
                "order_ref": "#1001",
                "idempotency_key": "safe-key",
            },
        )
    )

    assert result.ok is False
    assert result.error_code == "capability_provider_timeout"
    assert calls == ["shopify"]
    assert result.metadata["fallback_used"] is False
    assert (
        result.metadata["execution_attempts"][0]["fallback_allowed"]
        is False
    )
