from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.tcos.capabilities.compatibility import validate_capability_compatibility
from app.tcos.capabilities.models import CapabilityDefinition
from app.tcos.capabilities.scoring import score_capability
from app.tcos.capabilities.service import build_capability_registry


class CapabilityMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    required_inputs: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    allowed_categories: list[str] = Field(default_factory=list)
    allow_deprecated: bool = False
    allow_approval_required: bool = True
    limit: int = Field(default=10, ge=1, le=100)


class CapabilityMatch(BaseModel):
    capability: CapabilityDefinition
    score: float
    compatible: bool
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CapabilityMatchResponse(BaseModel):
    query: str
    matches: list[CapabilityMatch]


def match_capabilities(request: CapabilityMatchRequest) -> CapabilityMatchResponse:
    registry = build_capability_registry()
    candidates = registry.search(request.query)

    matches: list[CapabilityMatch] = []

    for capability in candidates:
        compatibility = validate_capability_compatibility(
            capability,
            required_inputs=request.required_inputs,
            allowed_domains=request.allowed_domains or None,
            allowed_categories=request.allowed_categories or None,
            allow_deprecated=request.allow_deprecated,
            allow_approval_required=request.allow_approval_required,
        )

        if not compatibility.compatible:
            continue

        matches.append(
            CapabilityMatch(
                capability=capability,
                score=score_capability(capability, query=request.query),
                compatible=True,
                reasons=compatibility.reasons,
                warnings=compatibility.warnings,
            )
        )

    matches.sort(key=lambda item: (-item.score, item.capability.id))

    return CapabilityMatchResponse(
        query=request.query,
        matches=matches[: request.limit],
    )
