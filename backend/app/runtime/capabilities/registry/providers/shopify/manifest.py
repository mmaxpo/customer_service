from __future__ import annotations

from app.runtime.capabilities.registry.registries import BindingRegistry
from app.runtime.capabilities.registry.registries import CapabilityRegistry
from app.runtime.capabilities.registry.registries import CapabilityAliasRegistry
from app.runtime.capabilities.registry.registries import ProviderRegistry
from app.runtime.capabilities.registry.contracts import (
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityDomain,
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
    capabilities.register_domain(
        CapabilityDomain(
            id="ecommerce",
            title="Ecommerce",
            description="Commerce capabilities for orders, refunds, fulfillment, and products.",
        )
    )

    capabilities.register_category(
        CapabilityCategory(
            id="ecommerce.orders",
            domain_id="ecommerce",
            title="Orders",
            description="Order lookup and order status capabilities.",
        )
    )

    capabilities.register_capability(
        CapabilityDefinition(
            id="ecommerce.orders.get",
            category_id="ecommerce.orders",
            title="Get Order",
            description="Retrieve an ecommerce order by reference.",
            semantic_key="order.lookup",
            required_inputs=("order_ref",),
            output_key="shopify_order",
            risk=CapabilityRisk.SAFE,
            tags=("ecommerce", "orders", "lookup", "shopify"),
            metadata={"legacy_ids": ("shopify.get_order",)},
        )
    )

    capabilities.register_capability(
        CapabilityDefinition(
            id="ecommerce.orders.action",
            category_id="ecommerce.orders",
            title="Perform Order Action",
            description=(
                "Perform a guarded ecommerce order action such as refund, "
                "cancel, address update, reship, or shipping-status lookup."
            ),
            semantic_key="order.action",
            required_inputs=("action", "order_ref"),
            optional_inputs=(
                "reason",
                "note",
                "new_address",
                "amount",
                "scope",
                "idempotency_key",
            ),
            output_key="shopify_order_action",
            risk=CapabilityRisk.HIGH,
            tags=("ecommerce", "orders", "action", "shopify"),
            metadata={
                "legacy_ids": ("shopify.order_action",),
                "supported_actions": (
                    "refund",
                    "cancel",
                    "update_shipping_address",
                    "reship",
                    "shipping_status",
                ),
            },
        )
    )

    capabilities.register_capability(
        CapabilityDefinition(
            id="ecommerce.orders.tracking",
            category_id="ecommerce.orders",
            title="Get Order Tracking",
            description="Retrieve shipping/tracking status for an order.",
            semantic_key="order.tracking",
            required_inputs=("order_ref",),
            optional_inputs=("idempotency_key",),
            output_key="shopify_order_tracking",
            risk=CapabilityRisk.SAFE,
            tags=("ecommerce", "orders", "tracking", "shopify"),
            metadata={"legacy_ids": ("shopify.get_order_tracking",)},
        )
    )

    capabilities.register_capability(
        CapabilityDefinition(
            id="ecommerce.orders.add_note",
            category_id="ecommerce.orders",
            title="Add Order Note",
            description="Attach an internal or customer-facing note to an order.",
            semantic_key="order.add_note",
            required_inputs=("order_ref", "note"),
            optional_inputs=("idempotency_key",),
            output_key="shopify_order_note",
            risk=CapabilityRisk.MEDIUM,
            tags=("ecommerce", "orders", "note", "shopify"),
            metadata={"legacy_ids": ("shopify.add_order_note",)},
        )
    )

    providers.register(
        CapabilityProvider(
            id="shopify",
            title="Shopify",
            kind=CapabilityProviderKind.BUILTIN,
            description="Shopify ecommerce provider.",
            requires_auth=True,
            supports_fallback=True,
            metadata={"integration": "shopify"},
        )
    )

    bindings.register(
        ProviderBinding(
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            runtime_node_type="capability.invoke",
            required_inputs=("order_ref",),
            output_key="shopify_order",
            priority=100,
            enabled=True,
            risk=CapabilityRisk.SAFE,
            requires_approval=False,
            metadata={"legacy_capability_id": "shopify.get_order"},
        )
    )

    bindings.register(
        ProviderBinding(
            capability_id="ecommerce.orders.action",
            provider_id="shopify",
            provider_ref="shopify.order_action",
            runtime_node_type="capability.invoke",
            required_inputs=("action", "order_ref"),
            optional_inputs=(
                "reason",
                "note",
                "new_address",
                "amount",
                "scope",
                "idempotency_key",
            ),
            output_key="shopify_order_action",
            priority=100,
            enabled=True,
            risk=CapabilityRisk.HIGH,
            requires_approval=True,
            metadata={
                "legacy_capability_id": "shopify.order_action",
                "supported_actions": (
                    "refund",
                    "cancel",
                    "update_shipping_address",
                    "reship",
                    "shipping_status",
                ),
            },
        )
    )

    bindings.register(
        ProviderBinding(
            capability_id="ecommerce.orders.tracking",
            provider_id="shopify",
            provider_ref="shopify.get_order_tracking",
            runtime_node_type="capability.invoke",
            required_inputs=("order_ref",),
            optional_inputs=("idempotency_key",),
            output_key="shopify_order_tracking",
            priority=100,
            enabled=True,
            risk=CapabilityRisk.SAFE,
            requires_approval=False,
            metadata={"legacy_capability_id": "shopify.get_order_tracking"},
        )
    )

    aliases.register("shopify.get_order", "ecommerce.orders.get")
    aliases.register(
        "shopify.order_action",
        "ecommerce.orders.action",
    )
    aliases.register(
        "shopify.get_order_tracking",
        "ecommerce.orders.tracking",
    )

    bindings.register(
        ProviderBinding(
            capability_id="ecommerce.orders.add_note",
            provider_id="shopify",
            provider_ref="shopify.add_order_note",
            runtime_node_type="capability.invoke",
            required_inputs=("order_ref", "note"),
            optional_inputs=("idempotency_key",),
            output_key="shopify_order_note",
            priority=100,
            enabled=True,
            risk=CapabilityRisk.MEDIUM,
            requires_approval=False,
            metadata={"legacy_capability_id": "shopify.add_order_note"},
        )
    )

    aliases.register(
        "shopify.add_order_note",
        "ecommerce.orders.add_note",
    )
