from app.runtime.capabilities.registry.contracts import (
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityDomain,
    CapabilityProvider,
    CapabilityProviderKind,
    CapabilityResolutionRequest,
    CapabilityResolutionResult,
    CapabilityRisk,
    ProviderBinding,
    RejectedProvider,
)


def test_capability_registry_v3_vocabulary_models():
    domain = CapabilityDomain(
        id="ecommerce",
        title="Ecommerce",
    )
    category = CapabilityCategory(
        id="ecommerce.orders",
        domain_id=domain.id,
        title="Orders",
    )
    capability = CapabilityDefinition(
        id="ecommerce.orders.get",
        category_id=category.id,
        title="Get Order",
        semantic_key="order.lookup",
        required_inputs=("order_ref",),
        output_key="shopify_order",
        tags=("orders", "lookup"),
    )
    provider = CapabilityProvider(
        id="shopify",
        title="Shopify",
        kind=CapabilityProviderKind.BUILTIN,
        requires_auth=True,
    )
    binding = ProviderBinding(
        capability_id=capability.id,
        provider_id=provider.id,
        provider_ref="shopify.get_order",
        runtime_node_type="capability.invoke",
        required_inputs=("order_ref",),
        output_key="shopify_order",
        risk=CapabilityRisk.SAFE,
    )

    assert domain.id == "ecommerce"
    assert category.domain_id == "ecommerce"
    assert capability.required_inputs == ("order_ref",)
    assert provider.kind == CapabilityProviderKind.BUILTIN
    assert binding.provider_ref == "shopify.get_order"


def test_capability_resolution_result_explains_selection_and_rejections():
    request = CapabilityResolutionRequest(
        capability_id="ecommerce.orders.get",
        preferred_provider_id="shopify",
        inputs={"order_ref": "#1001"},
    )

    result = CapabilityResolutionResult(
        ok=True,
        capability_id=request.capability_id,
        selected_provider_id="shopify",
        provider_ref="shopify.get_order",
        runtime_node_type="capability.invoke",
        required_inputs=("order_ref",),
        explanation="Selected Shopify because it is installed and has auth.",
        rejected_providers=(
            RejectedProvider(provider_id="woocommerce", reason="not_installed"),
        ),
    )

    assert result.ok is True
    assert result.selected_provider_id == "shopify"
    assert result.provider_ref == "shopify.get_order"
    assert result.rejected_providers[0].reason == "not_installed"
