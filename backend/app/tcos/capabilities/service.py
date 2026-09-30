from __future__ import annotations

from typing import Any
from uuid import UUID

from app.agents_runtime.tools import build_builtin_tool_registry
from app.agents_runtime.tools.schemas import ToolRiskLevel
from app.tcos.capabilities.models import (
    CapabilityDefinition,
    CapabilityRisk,
    CapabilitySource,
    CapabilityStatus,
)
from app.tcos.capabilities.registry import CapabilityRegistry
from app.tcos.capabilities.overrides import apply_metadata_override
from app.tcos.capabilities.repository import CapabilityMetadataRepository
from app.runtime.nodes.registry import list_registered_nodes




_AGENT_RISK_MAP = {
    ToolRiskLevel.SAFE: CapabilityRisk.SAFE,
    ToolRiskLevel.SENSITIVE: CapabilityRisk.SENSITIVE,
    ToolRiskLevel.DANGEROUS: CapabilityRisk.DANGEROUS,
}


def _capability_id_from_runtime_node(node_type: str) -> str:
    return f"runtime.{node_type.replace('.', '_')}"


def _capability_id_from_agent_tool(name: str) -> str:
    return f"agent_tool.{name}"


def _runtime_node_to_capability(item: dict[str, Any]) -> CapabilityDefinition:
    node_type = str(item["node_type"])
    category = str(item.get("category") or "general")

    return CapabilityDefinition(
        id=(
            str(item.get("discovery_id"))
            if item.get("discovery_id")
            else _capability_id_from_runtime_node(node_type)
        ),
        name=node_type,
        title=str(item.get("title") or node_type),
        description=str(
            ((item.get("schema") or {}).get("description"))
            or f"Execute runtime node `{node_type}`."
        ),
        domain=str(item.get("domain") or "platform"),
        category=category,
        source=CapabilitySource.RUNTIME_NODE,
        source_ref=node_type,
        status=CapabilityStatus.STABLE,
        risk_level=CapabilityRisk(
            str(item.get("risk_level") or "safe")
        ),
        requires_approval=bool(
            item.get("requires_approval")
        ),
        input_schema=item.get("schema") or {},
        metadata={
            "icon": item.get("icon"),
            "group": item.get("group"),
            "default_config": item.get("default_config") or {},
            "node_type": node_type,
        },
    )


def _agent_tool_to_capability(tool) -> CapabilityDefinition:
    return CapabilityDefinition(
        id=_capability_id_from_agent_tool(tool.name),
        name=tool.name,
        title=tool.name.replace("_", " ").title(),
        description=tool.description,
        domain="agent_tool",
        category="tool",
        source=CapabilitySource.AGENT_TOOL,
        source_ref=tool.name,
        status=CapabilityStatus.STABLE,
        risk_level=_AGENT_RISK_MAP.get(tool.risk_level, CapabilityRisk.SAFE),
        requires_approval=bool(tool.requires_approval),
        input_schema=tool.parameters or {},
        metadata={
            "tool_name": tool.name,
            "provider": "builtin",
        },
    )


def build_capability_registry() -> CapabilityRegistry:
    """
    Build capability discovery from the runtime nodes currently
    installed by the surrounding composition root.

    TCOS does not install Products or Providers itself.
    """
    capabilities: dict[str, CapabilityDefinition] = {}

    for item in list_registered_nodes():
        capability = _runtime_node_to_capability(item)
        capabilities[capability.id] = capability


    tool_registry = build_builtin_tool_registry()

    for tool in tool_registry.list():
        capability = _agent_tool_to_capability(tool)
        capabilities[capability.id] = capability

    return CapabilityRegistry(capabilities=capabilities)


async def build_capability_registry_for_tenant(
    *,
    db,
    tenant_id: UUID | None = None,
) -> CapabilityRegistry:
    registry = build_capability_registry()
    repo = CapabilityMetadataRepository(db)
    overrides = await repo.list_for_tenant(tenant_id=tenant_id)
    overrides_by_id = {override.capability_id: override for override in overrides}

    capabilities = {}

    for capability in registry.list():
        updated = apply_metadata_override(
            capability,
            overrides_by_id.get(capability.id),
        )
        if updated is not None:
            capabilities[updated.id] = updated

    return CapabilityRegistry(capabilities=capabilities)
