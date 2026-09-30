from __future__ import annotations

from app.tcos.capabilities.models import CapabilityDefinition
from app.tcos.capabilities.service import build_capability_registry


def list_capability_catalog() -> list[dict]:
    registry = build_capability_registry()
    return [_to_catalog_item(item) for item in registry.list()]


def _to_catalog_item(item: CapabilityDefinition) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "domain": item.domain,
        "category": item.category,
        "source": item.source,
        "source_ref": item.source_ref,
        "version": item.version,
        "status": item.status,
        "risk_level": item.risk_level,
        "requires_approval": item.requires_approval,
        "input_schema": item.input_schema,
        "metadata": item.metadata,
    }
