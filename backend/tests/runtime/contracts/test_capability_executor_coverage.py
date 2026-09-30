import pytest

from app.runtime.capabilities.execution import (
    build_default_executor_registry,
    validate_executor_coverage,
)
from app.runtime.capabilities.registry import (
    build_default_system,
)


def test_production_default_system_has_complete_executor_coverage():
    system = build_default_system()
    executors = build_default_executor_registry()

    report = validate_executor_coverage(
        system=system,
        executors=executors,
    )

    assert report.ok is True
    assert report.enabled_provider_refs == (
        "shopify.add_order_note",
        "shopify.get_order",
        "shopify.get_order_tracking",
        "shopify.order_action",
    )
    assert report.registered_provider_refs == (
        "shopify.add_order_note",
        "shopify.get_order",
        "shopify.get_order_tracking",
        "shopify.order_action",
    )
    assert report.missing_executor_refs == ()
    assert report.unused_executor_refs == ()


def test_production_default_system_excludes_mock_provider():
    system = build_default_system()

    assert system.providers.has("shopify") is True
    assert system.providers.has("mock") is False
    assert system.bindings.has(
        "ecommerce.orders.get",
        "shopify",
    ) is True
    assert system.bindings.has(
        "ecommerce.orders.get",
        "mock",
    ) is False


def test_test_system_can_include_mock_provider_explicitly():
    system = build_default_system(
        include_mock_provider=True,
    )

    assert system.providers.has("mock") is True
    assert system.bindings.has(
        "ecommerce.orders.get",
        "mock",
    ) is True


def test_coverage_report_detects_missing_mock_executor():
    system = build_default_system(
        include_mock_provider=True,
    )
    executors = build_default_executor_registry()

    report = validate_executor_coverage(
        system=system,
        executors=executors,
    )

    assert report.ok is False
    assert report.missing_executor_refs == (
        "mock.get_order",
    )

    with pytest.raises(
        ValueError,
        match=(
            "Enabled capability bindings are missing runtime executors: "
            "mock.get_order"
        ),
    ):
        report.require_complete()
