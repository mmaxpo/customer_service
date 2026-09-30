from __future__ import annotations

"""
Canonical legacy V2 capability contracts.

These contracts remain isolated for runtime backward compatibility. Current
semantic capability code must use capability_registry.contracts instead.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CapabilityProviderType(StrEnum):
    BUILTIN = "builtin"
    MCP = "mcp"
    PLUGIN = "plugin"
    API = "api"


class CapabilityRiskLevel(StrEnum):
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"


class CapabilityDefinition(BaseModel):
    id: str
    title: str
    description: str = ""

    category: str
    provider_type: CapabilityProviderType = CapabilityProviderType.BUILTIN
    provider_ref: str | None = None

    required_inputs: list[str] = Field(default_factory=list)
    optional_inputs: list[str] = Field(default_factory=list)
    output_key: str | None = None

    risk_level: CapabilityRiskLevel = CapabilityRiskLevel.SAFE
    requires_approval: bool = False

    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityCategory(BaseModel):
    id: str
    title: str
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "CapabilityProviderType",
    "CapabilityRiskLevel",
    "CapabilityDefinition",
    "CapabilityCategory",
]
