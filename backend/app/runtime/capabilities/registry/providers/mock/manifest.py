from __future__ import annotations

from app.runtime.capabilities.registry.registries import BindingRegistry
from app.runtime.capabilities.registry.registries import CapabilityRegistry
from app.runtime.capabilities.registry.registries import CapabilityAliasRegistry
from app.runtime.capabilities.registry.registries import ProviderRegistry
from app.runtime.capabilities.registry.contracts import (
    CapabilityProvider,
    CapabilityProviderKind,
    CapabilityRisk,
    ProviderBinding,
)


def register_manifest(
    *,
    capabilities: CapabilityRegistry,
    providers: ProviderRegistry,
    bindings: BindingRegistry,
    aliases: CapabilityAliasRegistry,
) -> None:

    if not capabilities.has_capability("ecommerce.orders.get"):
        return

    providers.register(
        CapabilityProvider(
            id="mock",
            title="Mock Provider",
            kind=CapabilityProviderKind.BUILTIN,
            description="Testing provider.",
            supports_fallback=True,
        )
    )

    bindings.register(
        ProviderBinding(
            capability_id="ecommerce.orders.get",
            provider_id="mock",
            provider_ref="mock.get_order",
            runtime_node_type="capability.invoke",
            required_inputs=("order_ref",),
            output_key="shopify_order",
            priority=10,
            enabled=True,
            risk=CapabilityRisk.SAFE,
        )
    )
