from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class CapabilityRuntimeMapping:
    capability_id: str
    node_type: str
    default_config: dict[str, Any] = field(
        default_factory=dict
    )


def runtime_mapping_for_capability(
    capability_id: str,
    *,
    is_semantic_capability: (
        Callable[[str], bool] | None
    ) = None,
    runtime_node_for_capability: (
        Callable[[str], str | None] | None
    ) = None,
) -> CapabilityRuntimeMapping | None:
    """
    Translate a planning capability into a runtime node.

    Core owns only generic aliases and generic capability classes.

    Semantic business capabilities compile through capability.invoke.
    Direct Product/Provider runtime nodes are resolved by composition.
    """
    runtime_node_overrides = {
        "runtime.web_fetch_extract": "web.fetch_extract",
        "runtime.web_search": "web.search",
        "runtime.knowledge_ingest": "knowledge.ingest",
        "runtime.kb_search": "kb.search",
        "runtime.llm_generate": "llm.generate",
        "runtime.agent_custom": "agent.custom",
    }

    if capability_id in runtime_node_overrides:
        return CapabilityRuntimeMapping(
            capability_id=capability_id,
            node_type=runtime_node_overrides[
                capability_id
            ],
        )

    if (
        is_semantic_capability is not None
        and is_semantic_capability(
            capability_id
        )
    ):
        return CapabilityRuntimeMapping(
            capability_id=capability_id,
            node_type="capability.invoke",
            default_config={
                "capability_id": capability_id,
            },
        )

    if runtime_node_for_capability is not None:
        node_type = runtime_node_for_capability(
            capability_id
        )

        if node_type:
            return CapabilityRuntimeMapping(
                capability_id=capability_id,
                node_type=node_type,
            )

    if capability_id.startswith("runtime."):
        node_type = (
            capability_id
            .removeprefix("runtime.")
            .replace("_", ".")
        )

        return CapabilityRuntimeMapping(
            capability_id=capability_id,
            node_type=node_type,
        )

    if capability_id.startswith("agent_tool."):
        tool_name = capability_id.removeprefix(
            "agent_tool."
        )

        return CapabilityRuntimeMapping(
            capability_id=capability_id,
            node_type="agent.custom",
            default_config={
                "backend": "pure",
                "pattern": "tool_agent",
                "tools": [tool_name],
                "max_steps": 3,
            },
        )

    return None
