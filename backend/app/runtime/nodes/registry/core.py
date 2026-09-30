from __future__ import annotations

from typing import Any, Dict, Optional, Type


from app.runtime.nodes.registry.ui import NODE_UI
from app.runtime.nodes.registry.defaults import default_config_for
from app.runtime.nodes.registry.models import NodeRegistration
from pydantic import BaseModel

NODE_REGISTRY: Dict[str, "NodeRegistration"] = {}


def register_node(
    type_name: str,
    node_cls,
    config_model: Optional[Type[BaseModel]] = None,
    *,
    title: str | None = None,
    icon: str | None = None,
    category: str | None = None,
    group: str | None = None,
    domain: str | None = None,
    risk_level: str = "safe",
    requires_approval: bool = False,
    side_effect: bool = False,
    replay_policy: str = "run",
    discovery_id: str | None = None,
):
    """
    Register a node implementation in the global node registry.

    This is usually called during app startup by register_builtin_nodes().

    Args:
        type_name: Public node type string used in workflow JSON.
        node_cls: Python class implementing async run(ctx, state, config).
        config_model: Optional Pydantic model for config validation.

    Example:
        register_node(
            "kb.search",
            KnowledgeSearchNode,
            KnowledgeSearchConfig,
        )

        reg = get_node("kb.search")
        assert reg.node_cls is KnowledgeSearchNode
    """
    ui = NODE_UI.get(
        type_name,
        {
            "title": type_name,
            "icon": "node",
            "category": "other",
            "group": "Other",
        },
    )

    resolved_title = str(
        title
        if title is not None
        else ui.get("title") or type_name
    ).strip()

    resolved_icon = str(
        icon
        if icon is not None
        else ui.get("icon") or "node"
    ).strip()

    resolved_category = str(
        category
        if category is not None
        else ui.get("category") or "other"
    ).strip()

    resolved_group = str(
        group
        if group is not None
        else ui.get("group") or "Other"
    ).strip()

    if not resolved_title:
        raise ValueError(
            "node discovery title cannot be empty"
        )

    if not resolved_icon:
        raise ValueError(
            "node discovery icon cannot be empty"
        )

    if not resolved_category:
        raise ValueError(
            "node discovery category cannot be empty"
        )

    if not resolved_group:
        raise ValueError(
            "node discovery group cannot be empty"
        )

    domain_by_category = {
        "trigger": "workflow",
        "knowledge": "knowledge",
        "agent": "agent",
        "routing": "control",
        "control": "control",
        "data": "data",
        "output": "communication",
        "web": "web",
        "platform": "platform",
    }

    resolved_domain = (
        str(domain).strip()
        if domain is not None
        else domain_by_category.get(
            resolved_category,
            "platform",
        )
    )

    if not resolved_domain:
        raise ValueError(
            "node discovery domain cannot be empty"
        )

    resolved_discovery_id = None

    if discovery_id is not None:
        resolved_discovery_id = str(
            discovery_id
        ).strip()

        if not resolved_discovery_id:
            raise ValueError(
                "node discovery_id cannot be empty"
            )

    normalized_risk = str(
        risk_level or ""
    ).strip().lower()

    if normalized_risk not in {
        "safe",
        "sensitive",
        "dangerous",
    }:
        raise ValueError(
            "node risk_level must be one of: "
            "safe, sensitive, dangerous"
        )

    normalized_replay_policy = str(
        replay_policy or ""
    ).strip().lower()

    if normalized_replay_policy not in {
        "run",
        "skip",
        "side_effect",
        "dangerous",
        "no_replay",
        "never",
    }:
        raise ValueError(
            "node replay_policy must be one of: "
            "run, skip, side_effect, dangerous, "
            "no_replay, never"
        )

    NODE_REGISTRY[type_name] = NodeRegistration(
        type_name=type_name,
        node_cls=node_cls,
        config_model=config_model,
        title=resolved_title,
        icon=resolved_icon,
        category=resolved_category,
        group=resolved_group,
        domain=resolved_domain,
        risk_level=normalized_risk,
        requires_approval=bool(
            requires_approval
        ),
        side_effect=bool(side_effect),
        replay_policy=normalized_replay_policy,
        discovery_id=resolved_discovery_id,
    )


def get_node(type_name: str) -> NodeRegistration:
    """
    Return the registered node implementation for a node type.

    Args:
        type_name: Node type string, e.g. "llm.generate".

    Returns:
        NodeRegistration: Registered node class and config model.

    Raises:
        ValueError: If the node type is not registered.

    Example:
        reg = get_node("response")
        node = reg.node_cls()
    """
    if type_name not in NODE_REGISTRY:
        raise ValueError(f"Node type '{type_name}' not registered")
    return NODE_REGISTRY[type_name]


def parse_node_config(
    type_name: str,
    raw_config: Dict[str, Any],
) -> BaseModel | Dict[str, Any]:
    """
    Validate and parse raw node config.

    If the node has a Pydantic config model, raw_config is validated through it.
    If no config model exists, raw_config is returned unchanged.

    Args:
        type_name: Node type string.
        raw_config: Raw config from node.data after template rendering.

    Returns:
        BaseModel | dict:
            Parsed Pydantic config model, or raw dict.

    Example:
        config = parse_node_config(
            "kb.search",
            {"nodeType": "kb.search", "query": "refund policy"},
        )

        # config.query is available if kb.search has a Pydantic model
    """
    reg = get_node(type_name)
    if reg.config_model is None:
        return raw_config
    return reg.config_model.model_validate(raw_config or {})


def list_registered_nodes() -> list[dict]:
    """
    Return the frontend node catalog.

    This exposes all registered runtime node types with:
        - node_type
        - title
        - icon
        - category
        - group
        - default_config
        - JSON schema

    The frontend can use this to render the node palette and know what config
    fields each node supports.

    Returns:
        list[dict]: Sorted node catalog by node_type.

    Example:
        catalog = list_registered_nodes()

        first = catalog[0]
        assert "node_type" in first
        assert "default_config" in first
        assert "schema" in first
    """
    out: list[dict] = []

    for type_name, reg in NODE_REGISTRY.items():
        schema: dict = {}
        if reg.config_model is not None:
            try:
                schema = reg.config_model.model_json_schema()
            except Exception:
                schema = {}

        default_config = default_config_for(type_name, reg)

        out.append(
            {
                "node_type": type_name,
                "title": reg.title,
                "icon": reg.icon,
                "category": reg.category,
                "group": reg.group,
                "domain": reg.domain,
                "risk_level": reg.risk_level,
                "requires_approval": reg.requires_approval,
                "discovery_id": reg.discovery_id,
                "default_config": default_config,
                "schema": schema,
            }
        )
    return sorted(out, key=lambda x: x["node_type"])
