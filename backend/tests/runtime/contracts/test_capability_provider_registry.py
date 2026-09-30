import pytest

from app.runtime.capabilities.registry.registries import CapabilityRegistry
from app.runtime.capabilities.registry.registries import ProviderRegistry
from app.runtime.capabilities.registry.contracts import (
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityDomain,
    CapabilityProvider,
    CapabilityProviderKind,
)


def test_capability_registry_registers_and_lists():
    registry = CapabilityRegistry()

    registry.register_domain(CapabilityDomain(id="ecommerce", title="Ecommerce"))
    registry.register_category(
        CapabilityCategory(id="ecommerce.orders", domain_id="ecommerce", title="Orders")
    )
    registry.register_capability(
        CapabilityDefinition(
            id="ecommerce.orders.get",
            category_id="ecommerce.orders",
            title="Get Order",
        )
    )

    assert registry.has_domain("ecommerce")
    assert registry.has_category("ecommerce.orders")
    assert registry.has_capability("ecommerce.orders.get")
    assert registry.get_capability("ecommerce.orders.get").title == "Get Order"
    assert [x.id for x in registry.list_by_domain("ecommerce")] == ["ecommerce.orders.get"]
    assert [x.id for x in registry.list_by_category("ecommerce.orders")] == ["ecommerce.orders.get"]


def test_capability_registry_overwrites_and_sorts():
    registry = CapabilityRegistry()
    registry.register_domain(CapabilityDomain(id="ecommerce", title="Old"))
    registry.register_domain(CapabilityDomain(id="ecommerce", title="New"))
    registry.register_domain(CapabilityDomain(id="aaa", title="AAA"))

    assert registry.get_domain("ecommerce").title == "New"
    assert [x.id for x in registry.list_domains()] == ["aaa", "ecommerce"]


def test_capability_registry_rejects_missing_parent():
    registry = CapabilityRegistry()

    with pytest.raises(ValueError):
        registry.register_category(
            CapabilityCategory(id="ecommerce.orders", domain_id="ecommerce", title="Orders")
        )

    registry.register_domain(CapabilityDomain(id="ecommerce", title="Ecommerce"))

    with pytest.raises(ValueError):
        registry.register_capability(
            CapabilityDefinition(
                id="ecommerce.orders.get",
                category_id="ecommerce.orders",
                title="Get Order",
            )
        )


def test_provider_registry_registers_overwrites_and_lists():
    registry = ProviderRegistry()

    registry.register(
        CapabilityProvider(id="shopify", title="Old Shopify", kind=CapabilityProviderKind.BUILTIN)
    )
    registry.register(
        CapabilityProvider(id="shopify", title="Shopify", kind=CapabilityProviderKind.BUILTIN)
    )
    registry.register(
        CapabilityProvider(id="mcp", title="MCP", kind=CapabilityProviderKind.MCP)
    )

    assert registry.has("shopify")
    assert registry.get("shopify").title == "Shopify"
    assert [x.id for x in registry.list()] == ["mcp", "shopify"]
    assert [x.id for x in registry.list_by_kind(CapabilityProviderKind.BUILTIN)] == ["shopify"]


def test_provider_registry_rejects_empty_id():
    registry = ProviderRegistry()

    with pytest.raises(ValueError):
        registry.register(
            CapabilityProvider(id="", title="Invalid", kind=CapabilityProviderKind.BUILTIN)
        )
