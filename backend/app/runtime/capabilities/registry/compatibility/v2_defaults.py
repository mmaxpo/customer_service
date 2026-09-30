from __future__ import annotations

from app.runtime.capabilities.registry.compatibility.v2_models import (
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityProviderType,
    CapabilityRiskLevel,
)
from app.runtime.capabilities.registry.compatibility.v2_registry import CapabilityRegistryV2


def build_default_capability_registry_v2() -> CapabilityRegistryV2:
    registry = CapabilityRegistryV2()

    registry.register_category(
        CapabilityCategory(
            id="customer_service",
            title="Customer Service",
            description="Capabilities for understanding and replying to customer support requests.",
        )
    )
    registry.register_category(
        CapabilityCategory(
            id="customer_service.extraction",
            title="Customer Service / Extraction",
            description="Extract structured values from customer messages.",
        )
    )
    registry.register_category(
        CapabilityCategory(
            id="ecommerce",
            title="Ecommerce",
            description="Capabilities for orders, refunds, fulfillment, and commerce actions.",
        )
    )
    registry.register_category(
        CapabilityCategory(
            id="ecommerce.orders",
            title="Ecommerce / Orders",
            description="Order lookup and order status capabilities.",
        )
    )
    registry.register_category(
        CapabilityCategory(
            id="runtime",
            title="Runtime",
            description="Generic workflow runtime capabilities.",
        )
    )
    registry.register_category(
        CapabilityCategory(
            id="runtime.communication",
            title="Runtime / Communication",
            description="Runtime response and communication capabilities.",
        )
    )

    registry.register(
        CapabilityDefinition(
            id="customer_service.extract_order_ref",
            title="Extract Order Reference",
            description="Extract an order reference such as #1001 from a customer message.",
            category="customer_service.extraction",
            provider_type=CapabilityProviderType.BUILTIN,
            provider_ref="customer_service.extract_order_ref",
            output_key="order_ref",
            risk_level=CapabilityRiskLevel.SAFE,
            tags=["customer_service", "orders", "extraction"],
        )
    )

    registry.register(
        CapabilityDefinition(
            id="shopify.get_order",
            title="Get Shopify Order",
            description="Retrieve a Shopify order by order reference.",
            category="ecommerce.orders",
            provider_type=CapabilityProviderType.BUILTIN,
            provider_ref="shopify.get_order",
            required_inputs=["order_ref"],
            output_key="shopify_order",
            risk_level=CapabilityRiskLevel.SAFE,
            tags=["shopify", "orders", "lookup"],
        )
    )

    registry.register(
        CapabilityDefinition(
            id="shopify.order_action",
            title="Perform Shopify Order Action",
            description="Perform a guarded Shopify order action such as refund, cancel, reship, or address update.",
            category="ecommerce.orders",
            provider_type=CapabilityProviderType.BUILTIN,
            provider_ref="shopify.order_action",
            required_inputs=["action", "order_ref"],
            optional_inputs=[
                "reason",
                "note",
                "new_address",
                "amount",
                "idempotency_key",
            ],
            risk_level=CapabilityRiskLevel.HIGH,
            requires_approval=True,
            tags=["shopify", "orders", "mutation", "approval"],
        )
    )

    registry.register(
        CapabilityDefinition(
            id="runtime.agent_custom",
            title="Custom Agent",
            description="Run the configured runtime agent node.",
            category="runtime",
            provider_type=CapabilityProviderType.BUILTIN,
            provider_ref="agent.custom",
            risk_level=CapabilityRiskLevel.MEDIUM,
            tags=["runtime", "agent"],
        )
    )

    registry.register(
        CapabilityDefinition(
            id="runtime.response",
            title="Runtime Response",
            description="Return a response from the workflow runtime.",
            category="runtime.communication",
            provider_type=CapabilityProviderType.BUILTIN,
            provider_ref="response",
            risk_level=CapabilityRiskLevel.SAFE,
            tags=["runtime", "response"],
        )
    )

    return registry
