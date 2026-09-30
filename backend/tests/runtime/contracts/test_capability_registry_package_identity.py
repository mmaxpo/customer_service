from pathlib import Path

import app.runtime.capabilities.registry as capability_registry
from app.runtime.capabilities.registry import (
    CapabilityRegistry,
    CapabilitySystem,
    build_default_system,
)
from app.runtime.capabilities.registry.compatibility import (
    RuntimeCapabilityRegistry,
    build_default_runtime_capability_registry,
)


def test_capability_registry_resolves_to_canonical_package():
    module_path = Path(capability_registry.__file__)

    assert module_path.name == "__init__.py"
    assert module_path.parent.name == "registry"


def test_standalone_module_collision_has_been_removed():
    repository_root = Path(__file__).resolve().parents[3]
    obsolete_module = (
        repository_root
        / "app"
        / "runtime"
        / "services"
        / "capability_registry.py"
    )

    assert obsolete_module.exists() is False


def test_current_and_compatibility_registries_remain_explicit():
    system = build_default_system()
    compatibility_registry = (
        build_default_runtime_capability_registry()
    )

    assert isinstance(system, CapabilitySystem)
    assert isinstance(system.capabilities, CapabilityRegistry)
    assert isinstance(
        compatibility_registry,
        RuntimeCapabilityRegistry,
    )
