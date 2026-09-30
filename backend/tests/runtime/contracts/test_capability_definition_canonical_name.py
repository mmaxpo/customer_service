from app.runtime.capabilities.registry.contracts import (
    CapabilityDefinition,
)
from app.runtime.capabilities.registry.defaults import (
    build_default_system,
)


def test_unversioned_definition_owns_current_implementation():
    assert CapabilityDefinition.__module__.endswith(
        ".capabilities.registry.contracts"
    )
    assert CapabilityDefinition.__name__ == "CapabilityDefinition"


def test_default_system_uses_canonical_definition_instances():
    capability = (
        build_default_system()
        .capabilities
        .get_capability("ecommerce.orders.get")
    )

    assert type(capability) is CapabilityDefinition
