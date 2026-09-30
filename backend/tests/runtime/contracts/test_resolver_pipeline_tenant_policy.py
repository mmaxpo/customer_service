from app.runtime.capabilities.registry.policies import (
    BindingEnabledPolicy,
    ResolutionContext,
    TenantAvailabilityPolicy,
)
from app.runtime.capabilities.registry.state import (
    TenantProviderRegistry,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    ProviderBinding,
)


def test_binding_enabled_policy_removes_disabled_bindings():
    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(capability_id="ecommerce.orders.get"),
        candidates=[
            ProviderBinding(
                capability_id="ecommerce.orders.get",
                provider_id="shopify",
                provider_ref="shopify.get_order",
                enabled=False,
            ),
            ProviderBinding(
                capability_id="ecommerce.orders.get",
                provider_id="mock",
                provider_ref="mock.get_order",
                enabled=True,
            ),
        ],
    )

    BindingEnabledPolicy().apply(ctx)

    assert [item.provider_id for item in ctx.candidates] == ["mock"]
    assert ctx.rejected[0].provider_id == "shopify"
    assert ctx.rejected[0].reason == "disabled"


def test_tenant_availability_policy_removes_disabled_tenant_provider():
    tenant_providers = TenantProviderRegistry()
    tenant_providers.disable(tenant_id="tenant_1", provider_id="shopify")
    tenant_providers.enable(tenant_id="tenant_1", provider_id="mock")

    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            tenant_id="tenant_1",
        ),
        candidates=[
            ProviderBinding(
                capability_id="ecommerce.orders.get",
                provider_id="shopify",
                provider_ref="shopify.get_order",
            ),
            ProviderBinding(
                capability_id="ecommerce.orders.get",
                provider_id="mock",
                provider_ref="mock.get_order",
            ),
        ],
    )

    TenantAvailabilityPolicy(tenant_providers).apply(ctx)

    assert [item.provider_id for item in ctx.candidates] == ["mock"]
    assert ctx.rejected[0].provider_id == "shopify"
    assert ctx.rejected[0].reason == "disabled_for_tenant"
