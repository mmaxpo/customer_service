from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Type

from pydantic import BaseModel


@dataclass(frozen=True)
class NodeRegistration:
    """
    Runtime registration record for one node type.

    Each workflow node type maps to:
        - type_name: public node type string, e.g. "kb.search"
        - node_cls: Python class that implements node.run(...)
        - config_model: optional Pydantic model for node config validation

    Example:
        NodeRegistration(
            type_name="kb.search",
            node_cls=KnowledgeSearchNode,
            config_model=KnowledgeSearchConfig,
        )
    """

    type_name: str
    node_cls: Type[Any]
    config_model: Optional[Type[BaseModel]] = None
    title: str = ""
    icon: str = "node"
    category: str = "other"
    group: str = "Other"
    domain: str = "platform"
    risk_level: str = "safe"
    requires_approval: bool = False
    side_effect: bool = False
    replay_policy: str = "run"
    discovery_id: str | None = None
