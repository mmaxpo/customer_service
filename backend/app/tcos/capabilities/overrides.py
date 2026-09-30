from __future__ import annotations

from app.tcos.capabilities.models import CapabilityDefinition, CapabilityStatus
from app.models.models import CapabilityMetadata


def apply_metadata_override(
    capability: CapabilityDefinition,
    override: CapabilityMetadata | None,
) -> CapabilityDefinition | None:
    if override is None:
        return capability

    if not override.is_enabled:
        return None

    data = capability.model_dump()

    if override.display_name:
        data["title"] = override.display_name

    if override.description:
        data["description"] = override.description

    if override.domain:
        data["domain"] = override.domain

    if override.category:
        data["category"] = override.category

    if override.status:
        data["status"] = CapabilityStatus(override.status)

    merged_metadata = dict(data.get("metadata") or {})
    merged_metadata.update(override.extra or {})
    merged_metadata["override_id"] = str(override.id)
    merged_metadata["override_tenant_id"] = (
        str(override.tenant_id) if override.tenant_id else None
    )
    merged_metadata["tags"] = override.tags or []

    data["metadata"] = merged_metadata

    return CapabilityDefinition.model_validate(data)
