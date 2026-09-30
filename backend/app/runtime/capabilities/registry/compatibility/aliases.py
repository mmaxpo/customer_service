from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CapabilityAliasRegistry:
    aliases: dict[str, str] = field(default_factory=dict)

    def register(self, legacy_id: str, semantic_id: str) -> None:
        legacy_id = str(legacy_id or "").strip()
        semantic_id = str(semantic_id or "").strip()

        if not legacy_id:
            raise ValueError("legacy_id cannot be empty")
        if not semantic_id:
            raise ValueError("semantic_id cannot be empty")

        self.aliases[legacy_id] = semantic_id

    def resolve(self, capability_id: str) -> str:
        return self.aliases.get(capability_id, capability_id)

    def has(self, legacy_id: str) -> bool:
        return legacy_id in self.aliases

    def list(self) -> list[tuple[str, str]]:
        return [(key, self.aliases[key]) for key in sorted(self.aliases)]
