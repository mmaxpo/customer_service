from app.runtime.capabilities.registry.state import (
    ProviderAuthRegistry,
)
from app.runtime.capabilities.registry.system import (
    build_default_system,
)
from app.runtime.capabilities.registry.state import (
    TenantProviderRegistry,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
)


def test_default_capability_system_loads_all_manifest_contributions_once():
    system = build_default_system(
        include_mock_provider=True,
    )

    assert system.capabilities.has_capability("ecommerce.orders.get")
    assert system.providers.has("shopify")
    assert system.providers.has("mock")
    assert system.bindings.has("ecommerce.orders.get", "shopify")
    assert system.bindings.has("ecommerce.orders.get", "mock")
    assert system.aliases.resolve("shopify.get_order") == "ecommerce.orders.get"


def test_capability_system_builds_resolver_from_same_registries():
    system = build_default_system()
    resolver = system.build_resolver()

    assert resolver.capabilities is system.capabilities
    assert resolver.providers is system.providers
    assert resolver.bindings is system.bindings
    assert resolver.aliases is system.aliases

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="shopify.get_order",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.capability_id == "ecommerce.orders.get"
    assert result.selected_provider_id == "shopify"


def test_capability_system_passes_tenant_and_auth_state_to_resolver():
    tenant_providers = TenantProviderRegistry()
    tenant_providers.enable(
        tenant_id="tenant_1",
        provider_id="shopify",
    )
    tenant_providers.enable(
        tenant_id="tenant_1",
        provider_id="mock",
    )

    provider_auth = ProviderAuthRegistry()

    system = build_default_system(
        tenant_providers=tenant_providers,
        provider_auth=provider_auth,
        include_mock_provider=True,
    )

    result_without_auth = system.build_resolver().resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            tenant_id="tenant_1",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result_without_auth.ok is True
    assert result_without_auth.selected_provider_id == "mock"

    provider_auth.connect(
        tenant_id="tenant_1",
        provider_id="shopify",
    )

    result_with_auth = system.build_resolver().resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            tenant_id="tenant_1",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result_with_auth.ok is True
    assert result_with_auth.selected_provider_id == "shopify"
