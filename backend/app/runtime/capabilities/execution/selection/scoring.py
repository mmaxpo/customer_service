from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from app.runtime.capabilities.execution.performance.queries import (
    CapabilityPerformanceQueryRepository,
)
from app.runtime.capabilities.registry.contracts import (
    ProviderBinding,
)


class ProviderCandidateScore(BaseModel):
    """
    Explainable score for one structurally eligible provider binding.

    Scores are advisory runtime-selection evidence. They do not mutate
    bindings, provider health, or durable learning state.
    """

    model_config = ConfigDict(extra="forbid")

    capability_id: str
    provider_id: str
    provider_ref: str
    binding_priority: int

    attempts: int = Field(default=0, ge=0)
    successes: int = Field(default=0, ge=0)
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    average_duration_ms: float = Field(default=0.0, ge=0.0)

    evidence_available: bool = False
    evidence_sufficient: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    priority_score: float = Field(ge=0.0, le=1.0)
    reliability_score: float = Field(ge=0.0, le=1.0)
    latency_score: float = Field(ge=0.0, le=1.0)
    final_score: float = Field(ge=0.0, le=1.0)

    selection_reason: str


class ProviderScoringResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str
    selected_provider_id: str | None = None
    selected_provider_ref: str | None = None

    scoring_applied: bool = False
    fallback_to_priority: bool = False
    reason: str

    window_hours: int = Field(default=24, ge=1)
    minimum_attempts: int = Field(default=10, ge=1)

    candidates: tuple[ProviderCandidateScore, ...] = ()


@runtime_checkable
class ProviderPerformanceScorer(Protocol):
    async def score_candidates(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        candidates: Sequence[ProviderBinding],
        observed_at: datetime | None = None,
    ) -> ProviderScoringResult:
        ...


class NullProviderPerformanceScorer:
    """
    Safe default preserving existing binding-priority selection exactly.
    """

    def __init__(
        self,
        *,
        window_hours: int = 24,
        minimum_attempts: int = 10,
    ) -> None:
        self.window_hours = window_hours
        self.minimum_attempts = minimum_attempts

    async def score_candidates(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        candidates: Sequence[ProviderBinding],
        observed_at: datetime | None = None,
    ) -> ProviderScoringResult:
        ordered = _priority_order(candidates)

        return ProviderScoringResult(
            capability_id=capability_id,
            selected_provider_id=(
                ordered[0].provider_id if ordered else None
            ),
            selected_provider_ref=(
                ordered[0].provider_ref if ordered else None
            ),
            scoring_applied=False,
            fallback_to_priority=True,
            reason="performance_scoring_not_configured",
            window_hours=self.window_hours,
            minimum_attempts=self.minimum_attempts,
            candidates=tuple(
                _priority_only_score(
                    binding=binding,
                    candidates=ordered,
                    reason="binding_priority",
                )
                for binding in ordered
            ),
        )


class DatabaseProviderPerformanceScorer:
    """
    Read-only, user/tenant-scoped provider performance scorer.

    The database query is observational and fail-open. Missing ownership,
    missing evidence, or query failure preserves deterministic binding
    priority.
    """

    def __init__(
        self,
        db,
        *,
        window_hours: int = 24,
        minimum_attempts: int = 10,
        priority_weight: float = 0.20,
        reliability_weight: float = 0.65,
        latency_weight: float = 0.15,
    ) -> None:
        if window_hours < 1:
            raise ValueError("window_hours must be >= 1")

        if minimum_attempts < 1:
            raise ValueError("minimum_attempts must be >= 1")

        weights = (
            priority_weight,
            reliability_weight,
            latency_weight,
        )

        if any(value < 0.0 for value in weights):
            raise ValueError("provider score weights must be >= 0")

        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError(
                "provider score weights must sum to 1.0"
            )

        self.repo = CapabilityPerformanceQueryRepository(db)
        self.window_hours = window_hours
        self.minimum_attempts = minimum_attempts
        self.priority_weight = priority_weight
        self.reliability_weight = reliability_weight
        self.latency_weight = latency_weight

    async def score_candidates(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        candidates: Sequence[ProviderBinding],
        observed_at: datetime | None = None,
    ) -> ProviderScoringResult:
        ordered = _priority_order(candidates)

        if not ordered:
            return ProviderScoringResult(
                capability_id=capability_id,
                reason="no_eligible_candidates",
                window_hours=self.window_hours,
                minimum_attempts=self.minimum_attempts,
            )

        if user_id is None:
            return self._priority_result(
                capability_id=capability_id,
                candidates=ordered,
                reason="missing_user_scope",
            )

        try:
            _, _, rows = await self.repo.summarize(
                user_id=user_id,
                tenant_id=tenant_id,
                capability_id=capability_id,
                window_hours=self.window_hours,
                now=observed_at,
            )
        except Exception:
            return self._priority_result(
                capability_id=capability_id,
                candidates=ordered,
                reason="performance_query_failed_open",
            )

        evidence = {
            (
                str(row.get("provider_id") or ""),
                str(row.get("provider_ref") or ""),
            ): row
            for row in rows
        }

        candidate_rows = [
            evidence.get(
                (binding.provider_id, binding.provider_ref)
            )
            for binding in ordered
        ]

        if not any(candidate_rows):
            return self._priority_result(
                capability_id=capability_id,
                candidates=ordered,
                reason="no_performance_evidence",
            )

        priorities = [binding.priority for binding in ordered]
        minimum_priority = min(priorities)
        maximum_priority = max(priorities)

        positive_latencies = [
            float(row.get("average_duration_ms") or 0.0)
            for row in candidate_rows
            if row is not None
            and float(row.get("average_duration_ms") or 0.0) > 0.0
        ]
        fastest_latency = (
            min(positive_latencies)
            if positive_latencies
            else None
        )

        scored: list[ProviderCandidateScore] = []

        for binding, row in zip(
            ordered,
            candidate_rows,
            strict=True,
        ):
            priority_score = _normalize_priority(
                binding.priority,
                minimum_priority=minimum_priority,
                maximum_priority=maximum_priority,
            )

            if row is None:
                neutral_reliability = 0.5
                neutral_latency = 0.5
                final_score = (
                    self.priority_weight * priority_score
                    + self.reliability_weight
                    * neutral_reliability
                    + self.latency_weight
                    * neutral_latency
                )

                scored.append(
                    ProviderCandidateScore(
                        capability_id=capability_id,
                        provider_id=binding.provider_id,
                        provider_ref=binding.provider_ref,
                        binding_priority=binding.priority,
                        priority_score=priority_score,
                        reliability_score=neutral_reliability,
                        latency_score=neutral_latency,
                        final_score=_bounded(final_score),
                        selection_reason=(
                            "neutral_prior_without_evidence"
                        ),
                    )
                )
                continue

            attempts = int(row.get("attempts") or 0)
            successes = int(row.get("successes") or 0)
            success_rate = (
                successes / attempts
                if attempts
                else 0.0
            )
            average_duration_ms = float(
                row.get("average_duration_ms") or 0.0
            )
            confidence = min(
                attempts / self.minimum_attempts,
                1.0,
            )

            latency_score = _latency_score(
                average_duration_ms=average_duration_ms,
                fastest_latency=fastest_latency,
            )

            # Unknown evidence starts from a neutral prior instead of
            # assuming either perfect or failed performance. As attempts
            # accumulate, observed reliability and latency replace that
            # neutral prior.
            blended_reliability = (
                (1.0 - confidence) * 0.5
                + confidence * success_rate
            )
            blended_latency = (
                (1.0 - confidence) * 0.5
                + confidence * latency_score
            )

            final_score = (
                self.priority_weight * priority_score
                + self.reliability_weight
                * blended_reliability
                + self.latency_weight
                * blended_latency
            )

            scored.append(
                ProviderCandidateScore(
                    capability_id=capability_id,
                    provider_id=binding.provider_id,
                    provider_ref=binding.provider_ref,
                    binding_priority=binding.priority,
                    attempts=attempts,
                    successes=successes,
                    success_rate=success_rate,
                    average_duration_ms=average_duration_ms,
                    evidence_available=True,
                    evidence_sufficient=(
                        attempts >= self.minimum_attempts
                    ),
                    confidence=confidence,
                    priority_score=priority_score,
                    reliability_score=success_rate,
                    latency_score=latency_score,
                    final_score=_bounded(final_score),
                    selection_reason=(
                        "performance_weighted"
                        if confidence >= 1.0
                        else "confidence_blended"
                    ),
                )
            )

        ranked = sorted(
            scored,
            key=lambda item: (
                -item.final_score,
                -item.binding_priority,
                item.provider_id,
                item.provider_ref,
            ),
        )
        selected = ranked[0]

        return ProviderScoringResult(
            capability_id=capability_id,
            selected_provider_id=selected.provider_id,
            selected_provider_ref=selected.provider_ref,
            scoring_applied=True,
            fallback_to_priority=False,
            reason="performance_ranked",
            window_hours=self.window_hours,
            minimum_attempts=self.minimum_attempts,
            candidates=tuple(ranked),
        )

    def _priority_result(
        self,
        *,
        capability_id: str,
        candidates: Sequence[ProviderBinding],
        reason: str,
    ) -> ProviderScoringResult:
        ordered = _priority_order(candidates)

        return ProviderScoringResult(
            capability_id=capability_id,
            selected_provider_id=ordered[0].provider_id,
            selected_provider_ref=ordered[0].provider_ref,
            scoring_applied=False,
            fallback_to_priority=True,
            reason=reason,
            window_hours=self.window_hours,
            minimum_attempts=self.minimum_attempts,
            candidates=tuple(
                _priority_only_score(
                    binding=binding,
                    candidates=ordered,
                    reason="binding_priority",
                )
                for binding in ordered
            ),
        )


def _priority_order(
    candidates: Sequence[ProviderBinding],
) -> list[ProviderBinding]:
    return sorted(
        candidates,
        key=lambda binding: (
            -binding.priority,
            binding.provider_id,
            binding.provider_ref,
        ),
    )


def _priority_only_score(
    *,
    binding: ProviderBinding,
    candidates: Sequence[ProviderBinding],
    reason: str,
) -> ProviderCandidateScore:
    priorities = [item.priority for item in candidates]

    return ProviderCandidateScore(
        capability_id=binding.capability_id,
        provider_id=binding.provider_id,
        provider_ref=binding.provider_ref,
        binding_priority=binding.priority,
        priority_score=_normalize_priority(
            binding.priority,
            minimum_priority=min(priorities),
            maximum_priority=max(priorities),
        ),
        reliability_score=0.0,
        latency_score=0.0,
        final_score=_normalize_priority(
            binding.priority,
            minimum_priority=min(priorities),
            maximum_priority=max(priorities),
        ),
        selection_reason=reason,
    )


def _normalize_priority(
    priority: int,
    *,
    minimum_priority: int,
    maximum_priority: int,
) -> float:
    if maximum_priority == minimum_priority:
        return 1.0

    return _bounded(
        (priority - minimum_priority)
        / (maximum_priority - minimum_priority)
    )


def _latency_score(
    *,
    average_duration_ms: float,
    fastest_latency: float | None,
) -> float:
    if (
        fastest_latency is None
        or fastest_latency <= 0.0
        or average_duration_ms <= 0.0
    ):
        return 0.0

    return _bounded(
        fastest_latency / average_duration_ms
    )


def _bounded(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


__all__ = [
    "DatabaseProviderPerformanceScorer",
    "NullProviderPerformanceScorer",
    "ProviderCandidateScore",
    "ProviderPerformanceScorer",
    "ProviderScoringResult",
]
