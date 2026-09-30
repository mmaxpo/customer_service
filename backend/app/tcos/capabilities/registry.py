from __future__ import annotations

from dataclasses import dataclass

from app.tcos.capabilities.models import CapabilityDefinition
from app.tcos.capabilities.compatibility import validate_capability_compatibility
from app.tcos.capabilities.scoring import score_capability


@dataclass
class CapabilityRegistry:
    capabilities: dict[str, CapabilityDefinition]

    def list(self) -> list[CapabilityDefinition]:
        return sorted(self.capabilities.values(), key=lambda item: item.id)

    def get(self, capability_id: str) -> CapabilityDefinition:
        try:
            return self.capabilities[capability_id]
        except KeyError as exc:
            raise ValueError(f"Unknown capability: {capability_id}") from exc

    def search(self, query: str | None = None) -> list[CapabilityDefinition]:
        if not query:
            return self.list()

        q = query.lower().strip()

        matches = [
            item
            for item in self.list()
            if q in item.id.lower()
            or q in item.name.lower()
            or q in item.title.lower()
            or q in item.description.lower()
            or q in item.domain.lower()
            or q in item.category.lower()
        ]

        return sorted(
            matches,
            key=lambda item: (-score_capability(item, query=query), item.id),
        )

    def discover(
        self,
        *,
        query: str | None = None,
        domain: str | None = None,
        category: str | None = None,
        limit: int | None = None,
    ) -> list[CapabilityDefinition]:
        items = self.search(query) if query else self.list()

        if domain:
            items = [item for item in items if item.domain == domain]

        if category:
            items = [item for item in items if item.category == category]

        items = sorted(
            items,
            key=lambda item: (-score_capability(item, query=query), item.id),
        )

        if limit is not None:
            return items[:limit]

        return items

    def compatible(
        self,
        *,
        query: str | None = None,
        required_inputs: list[str] | None = None,
        allowed_domains: list[str] | None = None,
        allowed_categories: list[str] | None = None,
        allow_deprecated: bool = False,
        allow_approval_required: bool = True,
        limit: int | None = None,
    ) -> list[CapabilityDefinition]:
        items = self.search(query) if query else self.list()
        compatible_items = []

        for item in items:
            result = validate_capability_compatibility(
                item,
                required_inputs=required_inputs,
                allowed_domains=allowed_domains,
                allowed_categories=allowed_categories,
                allow_deprecated=allow_deprecated,
                allow_approval_required=allow_approval_required,
            )
            if result.compatible:
                compatible_items.append(item)

        compatible_items = sorted(
            compatible_items,
            key=lambda item: (-score_capability(item, query=query), item.id),
        )

        if limit is not None:
            return compatible_items[:limit]

        return compatible_items
