from app.runtime.capabilities.registry import (
    CapabilityCategory,
    CapabilityDefinition,
)
from app.runtime.capabilities.registry.compatibility import (
    CapabilityCategoryV2,
    CapabilityDefinitionV2,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityCategory as SemanticCategory,
    CapabilityDefinition as SemanticDefinition,
)


def test_unversioned_package_root_contracts_are_semantic():
    assert CapabilityDefinition is SemanticDefinition
    assert CapabilityCategory is SemanticCategory


def test_v2_contracts_are_only_explicit_compatibility_exports():
    assert CapabilityDefinitionV2 is not CapabilityDefinition
    assert CapabilityCategoryV2 is not CapabilityCategory

    assert CapabilityDefinitionV2.__module__.endswith(
        ".compatibility.v2_models"
    )
    assert CapabilityCategoryV2.__module__.endswith(
        ".compatibility.v2_models"
    )
