from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from app.runtime.capabilities.execution.selection.scoring import (
    ProviderCandidateScore,
    ProviderScoringResult,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityRisk,
    ProviderBinding,
)


class ProviderAllocationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str
    provider_ref: str
    final_score: float = Field(ge=0.0, le=1.0)
    normalized_weight: float = Field(ge=0.0, le=1.0)
    bucket_start: int = Field(ge=0)
    bucket_end: int = Field(ge=0)


class ProviderAllocationResult(BaseModel):
    """
    Explainable deterministic provider-allocation decision.

    Allocation is advisory. Durable health enforcement remains the final
    safety gate before execution.
    """

    model_config = ConfigDict(extra="forbid")

    capability_id: str

    allocation_applied: bool = False
    reason: str

    selected_provider_id: str | None = None
    selected_provider_ref: str | None = None

    allocation_key: str | None = None
    bucket: int | None = Field(default=None, ge=0)

    bucket_count: int = Field(default=10_000, ge=100)
    competitive_margin: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
    )

    candidates: tuple[ProviderAllocationCandidate, ...] = ()


@runtime_checkable
class ProviderTrafficAllocator(Protocol):
    def allocate(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        correlation_id: str | None,
        capability_risk: CapabilityRisk,
        bindings: Sequence[ProviderBinding],
        scoring: ProviderScoringResult,
    ) -> ProviderAllocationResult:
        ...


class NullProviderTrafficAllocator:
    """
    Preserve the scorer's deterministic top-ranked provider.
    """

    def allocate(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        correlation_id: str | None,
        capability_risk: CapabilityRisk,
        bindings: Sequence[ProviderBinding],
        scoring: ProviderScoringResult,
    ) -> ProviderAllocationResult:
        return ProviderAllocationResult(
            capability_id=capability_id,
            allocation_applied=False,
            reason="traffic_allocation_not_configured",
            selected_provider_id=(
                scoring.selected_provider_id
            ),
            selected_provider_ref=(
                scoring.selected_provider_ref
            ),
        )


class DeterministicProviderTrafficAllocator:
    """
    Deterministically distribute SAFE capability traffic among providers
    whose evidence-backed scores are sufficiently close.

    The allocation key uses stable invocation scope rather than process-local
    randomness. Retries with the same correlation ID therefore select the same
    provider.
    """

    def __init__(
        self,
        *,
        competitive_margin: float = 0.05,
        bucket_count: int = 10_000,
        maximum_candidates: int = 3,
    ) -> None:
        if not 0.0 <= competitive_margin <= 1.0:
            raise ValueError(
                "competitive_margin must be between 0 and 1"
            )

        if bucket_count < 100:
            raise ValueError("bucket_count must be >= 100")

        if maximum_candidates < 2:
            raise ValueError(
                "maximum_candidates must be >= 2"
            )

        self.competitive_margin = competitive_margin
        self.bucket_count = bucket_count
        self.maximum_candidates = maximum_candidates

    def allocate(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        correlation_id: str | None,
        capability_risk: CapabilityRisk,
        bindings: Sequence[ProviderBinding],
        scoring: ProviderScoringResult,
    ) -> ProviderAllocationResult:
        default_result = self._top_ranked_result(
            capability_id=capability_id,
            scoring=scoring,
            reason="highest_scored_provider",
        )

        if capability_risk != CapabilityRisk.SAFE:
            return default_result.model_copy(
                update={"reason": "capability_not_safe"}
            )

        if not correlation_id:
            return default_result.model_copy(
                update={"reason": "missing_correlation_id"}
            )

        if not scoring.scoring_applied:
            return default_result.model_copy(
                update={"reason": "performance_scoring_not_applied"}
            )

        bindings_by_key = {
            (item.provider_id, item.provider_ref): item
            for item in bindings
        }

        ranked = list(scoring.candidates)

        if not ranked:
            return default_result.model_copy(
                update={"reason": "no_scored_candidates"}
            )

        top_score = ranked[0].final_score

        competitive: list[ProviderCandidateScore] = []

        for candidate in ranked:
            binding = bindings_by_key.get(
                (
                    candidate.provider_id,
                    candidate.provider_ref,
                )
            )

            if binding is None:
                continue

            if binding.risk != CapabilityRisk.SAFE:
                continue

            if binding.requires_approval:
                continue

            if not candidate.evidence_sufficient:
                continue

            if (
                top_score - candidate.final_score
                > self.competitive_margin
            ):
                continue

            competitive.append(candidate)

            if (
                len(competitive)
                >= self.maximum_candidates
            ):
                break

        if len(competitive) < 2:
            return default_result.model_copy(
                update={
                    "reason": (
                        "fewer_than_two_competitive_providers"
                    )
                }
            )

        allocation_key = "|".join(
            (
                str(tenant_id or ""),
                str(user_id or ""),
                capability_id,
                correlation_id,
            )
        )

        digest = hashlib.sha256(
            allocation_key.encode("utf-8")
        ).digest()
        bucket = int.from_bytes(
            digest[:8],
            byteorder="big",
            signed=False,
        ) % self.bucket_count

        weights = self._normalized_weights(
            competitive
        )
        allocated_candidates = self._build_ranges(
            candidates=competitive,
            weights=weights,
        )

        selected = next(
            (
                item
                for item in allocated_candidates
                if item.bucket_start
                <= bucket
                < item.bucket_end
            ),
            allocated_candidates[-1],
        )

        return ProviderAllocationResult(
            capability_id=capability_id,
            allocation_applied=True,
            reason="deterministic_competitive_allocation",
            selected_provider_id=selected.provider_id,
            selected_provider_ref=selected.provider_ref,
            allocation_key=allocation_key,
            bucket=bucket,
            bucket_count=self.bucket_count,
            competitive_margin=self.competitive_margin,
            candidates=tuple(allocated_candidates),
        )

    def _top_ranked_result(
        self,
        *,
        capability_id: str,
        scoring: ProviderScoringResult,
        reason: str,
    ) -> ProviderAllocationResult:
        return ProviderAllocationResult(
            capability_id=capability_id,
            allocation_applied=False,
            reason=reason,
            selected_provider_id=(
                scoring.selected_provider_id
            ),
            selected_provider_ref=(
                scoring.selected_provider_ref
            ),
            bucket_count=self.bucket_count,
            competitive_margin=self.competitive_margin,
        )

    @staticmethod
    def _normalized_weights(
        candidates: Sequence[ProviderCandidateScore],
    ) -> list[float]:
        raw = [
            max(float(item.final_score), 0.000001)
            for item in candidates
        ]
        total = sum(raw)

        return [
            item / total
            for item in raw
        ]

    def _build_ranges(
        self,
        *,
        candidates: Sequence[ProviderCandidateScore],
        weights: Sequence[float],
    ) -> list[ProviderAllocationCandidate]:
        ranges: list[ProviderAllocationCandidate] = []
        cursor = 0

        for index, (candidate, weight) in enumerate(
            zip(candidates, weights, strict=True)
        ):
            if index == len(candidates) - 1:
                end = self.bucket_count
            else:
                width = max(
                    1,
                    round(weight * self.bucket_count),
                )
                end = min(
                    self.bucket_count,
                    cursor + width,
                )

            ranges.append(
                ProviderAllocationCandidate(
                    provider_id=candidate.provider_id,
                    provider_ref=candidate.provider_ref,
                    final_score=candidate.final_score,
                    normalized_weight=weight,
                    bucket_start=cursor,
                    bucket_end=end,
                )
            )
            cursor = end

        if ranges:
            last = ranges[-1]
            if last.bucket_end != self.bucket_count:
                ranges[-1] = last.model_copy(
                    update={
                        "bucket_end": self.bucket_count
                    }
                )

        return ranges


__all__ = [
    "DeterministicProviderTrafficAllocator",
    "NullProviderTrafficAllocator",
    "ProviderAllocationCandidate",
    "ProviderAllocationResult",
    "ProviderTrafficAllocator",
]
