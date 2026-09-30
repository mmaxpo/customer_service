from __future__ import annotations

"""
Canonical legacy V2 capability registry.

Current semantic capability code must use capability_registry.registries.
"""

from dataclasses import dataclass, field

from app.runtime.capabilities.registry.compatibility.v2_models import (
    CapabilityCategory,
    CapabilityDefinition,
)


@dataclass
class CapabilityRegistryV2:
    categories: dict[str, CapabilityCategory] = field(default_factory=dict)
    capabilities: dict[str, CapabilityDefinition] = field(default_factory=dict)

    def register_category(self, category: CapabilityCategory) -> None:
        self.categories[category.id] = category

    def register(self, capability: CapabilityDefinition) -> None:
        if capability.category not in self.categories:
            parent = capability.category.split(".")[0]
            self.register_category(
                CapabilityCategory(
                    id=capability.category,
                    title=capability.category.replace(".", " / ").title(),
                    description=f"Auto-created category for {parent} capabilities.",
                )
            )

        self.capabilities[capability.id] = capability

    def get(self, capability_id: str) -> CapabilityDefinition:
        try:
            return self.capabilities[capability_id]
        except KeyError as exc:
            raise ValueError(
                f"No capability resolver registered for {capability_id}"
            ) from exc

    def has(self, capability_id: str) -> bool:
        return capability_id in self.capabilities

    def list(self, *, category: str | None = None) -> list[CapabilityDefinition]:
        items = list(self.capabilities.values())
        if category:
            items = [
                item
                for item in items
                if item.category == category or item.category.startswith(f"{category}.")
            ]
        return sorted(items, key=lambda item: item.id)


__all__ = [
    "CapabilityRegistryV2",
]
