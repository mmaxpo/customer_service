from __future__ import annotations

"""
Canonical registry implementations for the capability system.

Historical registry module paths remain as compatibility shims.
"""

from dataclasses import dataclass, field

from app.runtime.capabilities.registry.contracts import (
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityDomain,
)


@dataclass
class CapabilityRegistry:
    domains: dict[str, CapabilityDomain] = field(default_factory=dict)
    categories: dict[str, CapabilityCategory] = field(default_factory=dict)
    capabilities: dict[str, CapabilityDefinition] = field(default_factory=dict)

    def register_domain(self, domain: CapabilityDomain) -> None:
        if not domain.id.strip():
            raise ValueError("domain.id cannot be empty")
        self.domains[domain.id] = domain

    def register_category(self, category: CapabilityCategory) -> None:
        if not category.id.strip():
            raise ValueError("category.id cannot be empty")
        if category.domain_id not in self.domains:
            raise ValueError(f"Unknown capability domain: {category.domain_id}")
        self.categories[category.id] = category

    def register_capability(self, capability: CapabilityDefinition) -> None:
        if not capability.id.strip():
            raise ValueError("capability.id cannot be empty")
        if capability.category_id not in self.categories:
            raise ValueError(f"Unknown capability category: {capability.category_id}")
        self.capabilities[capability.id] = capability

    def get_domain(self, domain_id: str) -> CapabilityDomain:
        return self.domains[domain_id]

    def get_category(self, category_id: str) -> CapabilityCategory:
        return self.categories[category_id]

    def get_capability(self, capability_id: str) -> CapabilityDefinition:
        return self.capabilities[capability_id]

    def has_domain(self, domain_id: str) -> bool:
        return domain_id in self.domains

    def has_category(self, category_id: str) -> bool:
        return category_id in self.categories

    def has_capability(self, capability_id: str) -> bool:
        return capability_id in self.capabilities

    def list_domains(self) -> list[CapabilityDomain]:
        return [self.domains[k] for k in sorted(self.domains)]

    def list_categories(self) -> list[CapabilityCategory]:
        return [self.categories[k] for k in sorted(self.categories)]

    def list_capabilities(self) -> list[CapabilityDefinition]:
        return [self.capabilities[k] for k in sorted(self.capabilities)]

    def list_by_domain(self, domain_id: str) -> list[CapabilityDefinition]:
        category_ids = {
            c.id for c in self.categories.values() if c.domain_id == domain_id
        }
        return [
            c
            for c in self.list_capabilities()
            if c.category_id in category_ids
        ]

    def list_by_category(self, category_id: str) -> list[CapabilityDefinition]:
        return [
            c
            for c in self.list_capabilities()
            if c.category_id == category_id
        ]


from dataclasses import dataclass, field

from app.runtime.capabilities.registry.contracts import (
    CapabilityProvider,
    CapabilityProviderKind,
)


@dataclass
class ProviderRegistry:
    providers: dict[str, CapabilityProvider] = field(default_factory=dict)

    def register(self, provider: CapabilityProvider) -> None:
        if not provider.id.strip():
            raise ValueError("provider.id cannot be empty")
        self.providers[provider.id] = provider

    def get(self, provider_id: str) -> CapabilityProvider:
        return self.providers[provider_id]

    def has(self, provider_id: str) -> bool:
        return provider_id in self.providers

    def list(self) -> list[CapabilityProvider]:
        return [self.providers[k] for k in sorted(self.providers)]

    def list_by_kind(self, kind: CapabilityProviderKind) -> list[CapabilityProvider]:
        return [
            provider
            for provider in self.list()
            if provider.kind == kind
        ]


from dataclasses import dataclass, field

from app.runtime.capabilities.registry.contracts import ProviderBinding


@dataclass
class BindingRegistry:
    _bindings: dict[tuple[str, str], ProviderBinding] = field(default_factory=dict)

    def register(self, binding: ProviderBinding) -> None:
        capability_id = binding.capability_id.strip()
        provider_id = binding.provider_id.strip()

        if not capability_id:
            raise ValueError("capability_id cannot be empty")

        if not provider_id:
            raise ValueError("provider_id cannot be empty")

        self._bindings[(capability_id, provider_id)] = binding

    def get(
        self,
        capability_id: str,
        provider_id: str,
    ) -> ProviderBinding:
        return self._bindings[(capability_id, provider_id)]

    def has(
        self,
        capability_id: str,
        provider_id: str,
    ) -> bool:
        return (capability_id, provider_id) in self._bindings

    def list(self) -> list[ProviderBinding]:
        return sorted(
            self._bindings.values(),
            key=lambda b: (-b.priority, b.provider_id),
        )

    def list_for_capability(
        self,
        capability_id: str,
    ) -> list[ProviderBinding]:
        return sorted(
            (
                b
                for b in self._bindings.values()
                if b.capability_id == capability_id
            ),
            key=lambda b: (-b.priority, b.provider_id),
        )

    def list_for_provider(
        self,
        provider_id: str,
    ) -> list[ProviderBinding]:
        return sorted(
            (
                b
                for b in self._bindings.values()
                if b.provider_id == provider_id
            ),
            key=lambda b: (-b.priority, b.provider_id),
        )

from app.runtime.capabilities.registry.compatibility.aliases import (
    CapabilityAliasRegistry,
)


__all__ = [
    "CapabilityRegistry",
    "ProviderRegistry",
    "BindingRegistry",
    "CapabilityAliasRegistry",
]
