from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CapabilitySource(StrEnum):
    RUNTIME_NODE = "runtime_node"
    AGENT_TOOL = "agent_tool"


class CapabilityStatus(StrEnum):
    STABLE = "stable"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class CapabilityRisk(StrEnum):
    SAFE = "safe"
    SENSITIVE = "sensitive"
    DANGEROUS = "dangerous"


class CapabilityDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    title: str
    description: str = ""
    domain: str = "platform"
    category: str = "general"
    source: CapabilitySource
    source_ref: str
    version: str = "1.0"
    status: CapabilityStatus = CapabilityStatus.STABLE
    risk_level: CapabilityRisk = CapabilityRisk.SAFE
    requires_approval: bool = False
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
