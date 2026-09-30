from __future__ import annotations

from dataclasses import dataclass, field

from app.runtime.capabilities.registry.compatibility.v2_defaults import (
    build_default_capability_registry_v2,
)
from app.runtime.capabilities.registry.compatibility.v2_models import (
    CapabilityDefinition as CapabilityDefinitionV2,
)
from app.runtime.capabilities.registry.compatibility.v2_registry import CapabilityRegistryV2


@dataclass(frozen=True)
class RuntimeCapabilityDefinition:
    capability_id: str
    required_inputs: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)


class RuntimeCapabilityRegistry:
    def __init__(
        self,
        capabilities: dict[str, RuntimeCapabilityDefinition] | None = None,
        *,
        v2: CapabilityRegistryV2 | None = None,
    ):
        self._v2 = v2
        self.capabilities = capabilities or {}

        if self._v2 is not None and not self.capabilities:
            self.capabilities = {
                item.id: RuntimeCapabilityDefinition(
                    capability_id=item.id,
                    required_inputs=tuple(item.required_inputs),
                    metadata={
                        **item.metadata,
                        "domain": (
                            item.tags[0]
                            if item.tags
                            else item.category.split(".")[0]
                        ),
                        "category": item.category,
                        "provider_type": item.provider_type.value,
                        "provider_ref": item.provider_ref,
                        "risk_level": item.risk_level.value,
                        "requires_approval": item.requires_approval,
                        "output_key": item.output_key,
                        "tags": list(item.tags),
                    },
                )
                for item in self._v2.list()
            }

    def has(self, capability_id: str) -> bool:
        return capability_id in self.capabilities

    def get(self, capability_id: str) -> RuntimeCapabilityDefinition:
        if capability_id not in self.capabilities:
            raise ValueError(
                f"No capability resolver registered for {capability_id}"
            )
        return self.capabilities[capability_id]

    def list(self) -> list[RuntimeCapabilityDefinition]:
        return list(self.capabilities.values())

    def list_v2(self) -> list[CapabilityDefinitionV2]:
        return self._v2.list() if self._v2 is not None else []

    def get_v2(self, capability_id: str) -> CapabilityDefinitionV2:
        if self._v2 is None:
            raise ValueError(
                f"No capability resolver registered for {capability_id}"
            )
        return self._v2.get(capability_id)


def build_default_runtime_capability_registry() -> RuntimeCapabilityRegistry:
    return RuntimeCapabilityRegistry(
        v2=build_default_capability_registry_v2()
    )


__all__ = [
    "RuntimeCapabilityDefinition",
    "RuntimeCapabilityRegistry",
    "build_default_runtime_capability_registry",
]
