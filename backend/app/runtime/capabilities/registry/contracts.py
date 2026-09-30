from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CapabilityProviderKind(StrEnum):
    BUILTIN = "builtin"
    PLUGIN = "plugin"
    MCP = "mcp"
    API = "api"


class CapabilityRisk(StrEnum):
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"


class CapabilityDomain(BaseModel):
    id: str
    title: str
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityCategory(BaseModel):
    id: str
    domain_id: str
    title: str
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityDefinition(BaseModel):
    id: str
    category_id: str
    title: str
    description: str = ""

    semantic_key: str | None = None
    required_inputs: tuple[str, ...] = ()
    optional_inputs: tuple[str, ...] = ()
    output_key: str | None = None

    risk: CapabilityRisk = CapabilityRisk.SAFE
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityProvider(BaseModel):
    id: str
    title: str
    kind: CapabilityProviderKind
    description: str = ""

    requires_auth: bool = False
    supports_fallback: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderBinding(BaseModel):
    capability_id: str
    provider_id: str

    provider_ref: str
    runtime_node_type: str = "capability.invoke"

    required_inputs: tuple[str, ...] = ()
    optional_inputs: tuple[str, ...] = ()
    output_key: str | None = None

    priority: int = 100
    enabled: bool = True
    risk: CapabilityRisk = CapabilityRisk.SAFE
    requires_approval: bool = False

    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityResolutionRequest(BaseModel):
    capability_id: str
    user_id: str | None = None
    tenant_id: str | None = None

    preferred_provider_id: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    max_cost: float | None = None
    max_latency_ms: int | None = None
    max_risk: CapabilityRisk | None = None
    allow_approval_required: bool = True
    allowed_provider_ids: tuple[str, ...] = ()
    denied_provider_ids: tuple[str, ...] = ()
    required_region: str | None = None
    required_action: str | None = None


class RejectedProvider(BaseModel):
    provider_id: str
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityResolutionResult(BaseModel):
    ok: bool
    capability_id: str

    selected_provider_id: str | None = None
    provider_ref: str | None = None
    runtime_node_type: str | None = None

    required_inputs: tuple[str, ...] = ()
    missing_inputs: tuple[str, ...] = ()

    requires_approval: bool = False
    risk: CapabilityRisk = CapabilityRisk.SAFE

    rejected_providers: tuple[RejectedProvider, ...] = ()
    explanation: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "CapabilityProviderKind",
    "CapabilityRisk",
    "CapabilityDomain",
    "CapabilityCategory",
    "CapabilityDefinition",
    "CapabilityProvider",
    "ProviderBinding",
    "CapabilityResolutionRequest",
    "RejectedProvider",
    "CapabilityResolutionResult",
]
