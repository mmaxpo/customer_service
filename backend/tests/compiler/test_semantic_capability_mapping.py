from __future__ import annotations

from app.runtime.capabilities.registry.defaults import (
    build_default_capability_registry,
)
from app.tcos.compiler.capability_mapping import (
    runtime_mapping_for_capability,
)


def test_registered_semantic_capability_maps_to_generic_invoke():
    registry = build_default_capability_registry()

    mapping = runtime_mapping_for_capability(
        "ecommerce.orders.get",
        is_semantic_capability=registry.has_capability,
    )

    assert mapping is not None
    assert mapping.capability_id == "ecommerce.orders.get"
    assert mapping.node_type == "capability.invoke"

    assert mapping.default_config == {
        "capability_id": "ecommerce.orders.get",
    }


def test_semantic_mapping_is_not_domain_prefix_based():
    registered = {
        "logistics.shipments.track",
        "crm.customers.lookup",
    }

    def has_capability(capability_id: str) -> bool:
        return capability_id in registered

    logistics = runtime_mapping_for_capability(
        "logistics.shipments.track",
        is_semantic_capability=has_capability,
    )

    crm = runtime_mapping_for_capability(
        "crm.customers.lookup",
        is_semantic_capability=has_capability,
    )

    assert logistics is not None
    assert logistics.node_type == "capability.invoke"

    assert crm is not None
    assert crm.node_type == "capability.invoke"


def test_unregistered_domain_shaped_id_is_not_semantic():
    def has_capability(capability_id: str) -> bool:
        return False

    mapping = runtime_mapping_for_capability(
        "ecommerce.fake.capability",
        is_semantic_capability=has_capability,
    )

    assert mapping is None


def test_no_predicate_preserves_existing_behavior():
    assert runtime_mapping_for_capability("ecommerce.orders.get") is None


def test_provider_node_requires_injected_runtime_resolver():
    assert (
        runtime_mapping_for_capability(
            "shopify.get_order",
        )
        is None
    )

    mapping = runtime_mapping_for_capability(
        "shopify.get_order",
        runtime_node_for_capability=lambda capability_id: (
            "shopify.get_order"
            if capability_id == "shopify.get_order"
            else None
        ),
    )

    assert mapping is not None
    assert mapping.node_type == "shopify.get_order"
    assert mapping.default_config == {}


def test_explicit_runtime_mapping_wins_before_semantic_predicate():
    def claims_everything(capability_id: str) -> bool:
        return True

    mapping = runtime_mapping_for_capability(
        "runtime.agent_custom",
        is_semantic_capability=claims_everything,
    )

    assert mapping is not None
    assert mapping.node_type == "agent.custom"

def test_registered_runtime_node_mapping_is_not_prefix_based():
    mapping = runtime_mapping_for_capability(
        "warehouse.inventory.lookup",
        runtime_node_for_capability=lambda capability_id: (
            "inventory.lookup"
            if capability_id == "warehouse.inventory.lookup"
            else None
        ),
    )

    assert mapping is not None
    assert mapping.capability_id == "warehouse.inventory.lookup"
    assert mapping.node_type == "inventory.lookup"
    assert mapping.default_config == {}


def test_unknown_runtime_node_remains_uncompilable():
    assert (
        runtime_mapping_for_capability(
            "warehouse.inventory.unknown",
            runtime_node_for_capability=lambda _: None,
        )
        is None
    )
