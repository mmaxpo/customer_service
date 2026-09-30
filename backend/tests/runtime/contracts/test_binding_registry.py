import pytest

from app.runtime.capabilities.registry.registries import BindingRegistry
from app.runtime.capabilities.registry.contracts import (
    CapabilityRisk,
    ProviderBinding,
)


def binding(
    capability="ecommerce.orders.get",
    provider="shopify",
    priority=100,
):
    return ProviderBinding(
        capability_id=capability,
        provider_id=provider,
        provider_ref=f"{provider}.get_order",
        runtime_node_type="capability.invoke",
        required_inputs=("order_ref",),
        output_key="shopify_order",
        priority=priority,
        risk=CapabilityRisk.SAFE,
    )


def test_register_and_lookup():
    registry = BindingRegistry()

    b = binding()

    registry.register(b)

    assert registry.has(
        "ecommerce.orders.get",
        "shopify",
    )

    assert registry.get(
        "ecommerce.orders.get",
        "shopify",
    ) == b


def test_duplicate_registration_overwrites():
    registry = BindingRegistry()

    registry.register(binding(priority=10))
    registry.register(binding(priority=999))

    assert registry.get(
        "ecommerce.orders.get",
        "shopify",
    ).priority == 999


def test_list_returns_all():
    registry = BindingRegistry()

    registry.register(binding(provider="shopify"))
    registry.register(binding(provider="woocommerce"))

    assert len(registry.list()) == 2


def test_list_for_capability():
    registry = BindingRegistry()

    registry.register(binding(provider="shopify"))
    registry.register(binding(provider="woocommerce"))
    registry.register(
        binding(
            capability="crm.customer.lookup",
            provider="hubspot",
        )
    )

    items = registry.list_for_capability(
        "ecommerce.orders.get"
    )

    assert len(items) == 2


def test_list_for_provider():
    registry = BindingRegistry()

    registry.register(binding(provider="shopify"))

    registry.register(
        binding(
            capability="ecommerce.orders.refund",
            provider="shopify",
        )
    )

    assert len(registry.list_for_provider("shopify")) == 2


def test_priority_sorting():
    registry = BindingRegistry()

    registry.register(binding(provider="shopify", priority=10))
    registry.register(binding(provider="woocommerce", priority=100))

    items = registry.list()

    assert items[0].provider_id == "woocommerce"
    assert items[1].provider_id == "shopify"


def test_deterministic_ordering_same_priority():
    registry = BindingRegistry()

    registry.register(binding(provider="zzz", priority=10))
    registry.register(binding(provider="aaa", priority=10))

    items = registry.list()

    assert [x.provider_id for x in items] == [
        "aaa",
        "zzz",
    ]


def test_invalid_empty_capability():
    registry = BindingRegistry()

    with pytest.raises(ValueError):
        registry.register(
            ProviderBinding(
                capability_id="",
                provider_id="shopify",
                provider_ref="shopify.get_order",
            )
        )


def test_invalid_empty_provider():
    registry = BindingRegistry()

    with pytest.raises(ValueError):
        registry.register(
            ProviderBinding(
                capability_id="ecommerce.orders.get",
                provider_id="",
                provider_ref="shopify.get_order",
            )
        )
