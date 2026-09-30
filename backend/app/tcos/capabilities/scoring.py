from __future__ import annotations

from app.tcos.capabilities.models import (
    CapabilityDefinition,
    CapabilityRisk,
    CapabilityStatus,
)


_STATUS_SCORE = {
    CapabilityStatus.STABLE: 1.0,
    CapabilityStatus.EXPERIMENTAL: 0.75,
    CapabilityStatus.DEPRECATED: 0.25,
}

_RISK_SCORE = {
    CapabilityRisk.SAFE: 1.0,
    CapabilityRisk.SENSITIVE: 0.7,
    CapabilityRisk.DANGEROUS: 0.35,
}


def score_capability(
    capability: CapabilityDefinition, *, query: str | None = None
) -> float:
    score = 0.0

    score += _STATUS_SCORE.get(capability.status, 0.0) * 40
    score += _RISK_SCORE.get(capability.risk_level, 0.0) * 20

    if not capability.requires_approval:
        score += 10

    if capability.input_schema:
        score += 10

    if query:
        q = query.lower().strip()
        searchable = " ".join(
            [
                capability.id,
                capability.name,
                capability.title,
                capability.description,
                capability.domain,
                capability.category,
            ]
        ).lower()

        if q == capability.id.lower() or q == capability.name.lower():
            score += 20
        elif q in searchable:
            score += 10

    return round(score, 4)
