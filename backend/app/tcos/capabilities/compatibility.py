from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.tcos.capabilities.models import CapabilityDefinition, CapabilityStatus


@dataclass(frozen=True)
class CapabilityCompatibilityResult:
    compatible: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_capability_compatibility(
    capability: CapabilityDefinition,
    *,
    required_inputs: list[str] | None = None,
    allowed_domains: list[str] | None = None,
    allowed_categories: list[str] | None = None,
    allow_deprecated: bool = False,
    allow_approval_required: bool = True,
) -> CapabilityCompatibilityResult:
    reasons: list[str] = []
    warnings: list[str] = []

    if capability.status == CapabilityStatus.DEPRECATED and not allow_deprecated:
        reasons.append("Capability is deprecated.")

    if capability.requires_approval and not allow_approval_required:
        reasons.append("Capability requires approval.")

    if allowed_domains and capability.domain not in allowed_domains:
        reasons.append(f"Capability domain `{capability.domain}` is not allowed.")

    if allowed_categories and capability.category not in allowed_categories:
        reasons.append(f"Capability category `{capability.category}` is not allowed.")

    required_inputs = required_inputs or []
    schema = capability.input_schema or {}
    properties: dict[str, Any] = schema.get("properties") or {}

    for required_input in required_inputs:
        if required_input not in properties:
            reasons.append(f"Missing required input `{required_input}`.")

    if not schema:
        warnings.append("Capability has no declared input schema.")

    return CapabilityCompatibilityResult(
        compatible=not reasons,
        reasons=reasons,
        warnings=warnings,
    )
