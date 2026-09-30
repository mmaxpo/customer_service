from app.runtime.capabilities.registry.compatibility import (
    CapabilityCategoryV2,
    CapabilityDefinitionV2,
    CapabilityRegistryV2,
)
from app.runtime.capabilities.registry.compatibility.v2_models import (
    CapabilityCategory,
    CapabilityDefinition,
)
from app.runtime.capabilities.registry.compatibility.v2_registry import (
    CapabilityRegistryV2 as CanonicalCapabilityRegistryV2,
)


def test_compatibility_package_owns_v2_contracts():
    assert CapabilityDefinition.__module__.endswith(
        ".compatibility.v2_models"
    )
    assert CapabilityCategory.__module__.endswith(
        ".compatibility.v2_models"
    )

    assert CapabilityDefinitionV2 is CapabilityDefinition
    assert CapabilityCategoryV2 is CapabilityCategory


def test_compatibility_package_owns_v2_registry():
    assert CanonicalCapabilityRegistryV2.__module__.endswith(
        ".compatibility.v2_registry"
    )
    assert CapabilityRegistryV2 is CanonicalCapabilityRegistryV2


def test_v2_registry_behavior_is_preserved():
    assert CapabilityRegistryV2().list() == []
