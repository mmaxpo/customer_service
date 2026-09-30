from app.runtime.capabilities.registry.defaults import (
    build_default_system as DefaultsBuildDefaultSystem,
)
from app.runtime.capabilities.registry.defaults.builders import (
    build_default_system as BuildersBuildDefaultSystem,
)
from app.runtime.capabilities.registry.system import (
    CapabilitySystem,
    build_default_system,
)


def test_system_module_owns_default_system_builder():
    assert build_default_system.__module__.endswith(
        ".capabilities.registry.system"
    )


def test_defaults_package_reexports_canonical_system_builder():
    assert DefaultsBuildDefaultSystem is build_default_system
    assert BuildersBuildDefaultSystem is build_default_system


def test_canonical_system_builder_preserves_default_components():
    system = build_default_system()

    assert isinstance(system, CapabilitySystem)
    assert system.capabilities.has_capability(
        "ecommerce.orders.get"
    )
    assert system.providers.has("shopify")
    assert not system.providers.has("mock")
    assert system.bindings.has(
        "ecommerce.orders.get",
        "shopify",
    )
    assert not system.bindings.has(
        "ecommerce.orders.get",
        "mock",
    )
