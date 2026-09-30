from app.runtime.capabilities.execution import (
    CapabilityExecutorRegistry,
)
from app.runtime.capabilities.registry import (
    CapabilitySystem,
    CapabilityRegistry,
)
from app.runtime.resources import RuntimeServiceFactory


def test_runtime_factory_uses_canonical_capability_system():
    services = RuntimeServiceFactory.build(
        user_id="user_1",
        tenant_id="tenant_1",
    )

    assert isinstance(
        services.capability_system,
        CapabilitySystem,
    )
    assert isinstance(
        services.capability_registry,
        CapabilityRegistry,
    )
    assert services.capability_registry is (
        services.capability_system.capabilities
    )
    assert services.capabilities.resolver.system is (
        services.capability_system
    )


def test_runtime_factory_builds_default_capability_executor_registry():
    services = RuntimeServiceFactory.build(
        user_id="user_1",
    )

    assert isinstance(
        services.capability_executors,
        CapabilityExecutorRegistry,
    )
    assert services.capability_executors.has(
        "shopify.get_order"
    )
    assert services.capability_executors.has(
        "shopify.order_action"
    )
    assert services.capabilities.resolver.executor_registry is (
        services.capability_executors
    )


def test_runtime_factory_excludes_test_only_mock_provider():
    services = RuntimeServiceFactory.build(
        user_id="user_1",
    )

    assert services.capability_system.providers.has(
        "shopify"
    )
    assert not services.capability_system.providers.has(
        "mock"
    )
    assert not services.capability_system.bindings.has(
        "ecommerce.orders.get",
        "mock",
    )
