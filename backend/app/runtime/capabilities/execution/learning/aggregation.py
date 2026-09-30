from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timezone
from enum import StrEnum
from math import sqrt
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


SUPPORTED_OUTCOMES = (
    "verified",
    "partially_verified",
    "failed",
    "inconclusive",
    "not_verifiable",
)


class CapabilityLearningQualityLevel(StrEnum):
    INSUFFICIENT = "insufficient"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class CapabilityLearningInterpretation(StrEnum):
    POSITIVE = "positive"
    MIXED = "mixed"
    NEGATIVE = "negative"
    UNRESOLVED = "unresolved"
    INSUFFICIENT_EVIDENCE = (
        "insufficient_evidence"
    )


class CapabilityLearningSummary(BaseModel):
    """
    Advisory interpretation of immutable business-outcome evidence.

    This summary does not alter provider selection, traffic allocation,
    provider health, or runtime policy.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    capability_id: str
    provider_id: str | None = None
    provider_ref: str | None = None
    tenant_id: str | None = None
    action: str | None = None

    window_start: datetime | None = None
    window_end: datetime | None = None

    total_observations: int = Field(ge=0)
    final_observations: int = Field(ge=0)
    retryable_observations: int = Field(ge=0)
    observations_with_evidence: int = Field(ge=0)

    verified: int = Field(ge=0)
    partially_verified: int = Field(ge=0)
    failed: int = Field(ge=0)
    inconclusive: int = Field(ge=0)
    not_verifiable: int = Field(ge=0)

    average_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )
    evidence_coverage: float = Field(
        ge=0.0,
        le=1.0,
    )
    finality_ratio: float = Field(
        ge=0.0,
        le=1.0,
    )

    effective_sample_size: float = Field(
        ge=0.0
    )
    weighted_positive_mass: float = Field(
        ge=0.0
    )
    weighted_negative_mass: float = Field(
        ge=0.0
    )
    weighted_unresolved_mass: float = Field(
        ge=0.0
    )

    estimated_success_rate: float = Field(
        ge=0.0,
        le=1.0,
    )
    summary_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    minimum_effective_sample_size: float = (
        Field(ge=0.1)
    )
    evidence_sufficient: bool

    dominant_outcome: str | None = None
    quality_level: CapabilityLearningQualityLevel
    interpretation: CapabilityLearningInterpretation


class CapabilityLearningAggregationPolicy:
    """
    Deterministic policy for interpreting business-outcome evidence.

    Confidence is derived from:
      1. observation confidence,
      2. finality,
      3. normalized evidence presence,
      4. effective sample size.

    No time decay is applied in 2B-2A. A bounded query window will be
    introduced in the database-backed aggregation slice.
    """

    def __init__(
        self,
        *,
        minimum_effective_sample_size: float = 5.0,
        high_quality_threshold: float = 0.80,
        moderate_quality_threshold: float = 0.55,
        positive_threshold: float = 0.70,
        negative_threshold: float = 0.40,
        partial_success_value: float = 0.50,
        non_final_weight: float = 0.35,
        missing_evidence_weight: float = 0.75,
    ) -> None:
        if minimum_effective_sample_size <= 0.0:
            raise ValueError(
                "minimum_effective_sample_size "
                "must be > 0"
            )

        for name, value in (
            (
                "high_quality_threshold",
                high_quality_threshold,
            ),
            (
                "moderate_quality_threshold",
                moderate_quality_threshold,
            ),
            (
                "positive_threshold",
                positive_threshold,
            ),
            (
                "negative_threshold",
                negative_threshold,
            ),
            (
                "partial_success_value",
                partial_success_value,
            ),
            (
                "non_final_weight",
                non_final_weight,
            ),
            (
                "missing_evidence_weight",
                missing_evidence_weight,
            ),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1"
                )

        if (
            moderate_quality_threshold
            > high_quality_threshold
        ):
            raise ValueError(
                "moderate_quality_threshold cannot "
                "exceed high_quality_threshold"
            )

        if negative_threshold > positive_threshold:
            raise ValueError(
                "negative_threshold cannot exceed "
                "positive_threshold"
            )

        self.minimum_effective_sample_size = (
            minimum_effective_sample_size
        )
        self.high_quality_threshold = (
            high_quality_threshold
        )
        self.moderate_quality_threshold = (
            moderate_quality_threshold
        )
        self.positive_threshold = (
            positive_threshold
        )
        self.negative_threshold = (
            negative_threshold
        )
        self.partial_success_value = (
            partial_success_value
        )
        self.non_final_weight = non_final_weight
        self.missing_evidence_weight = (
            missing_evidence_weight
        )

    def quality_level(
        self,
        *,
        summary_confidence: float,
        evidence_sufficient: bool,
    ) -> CapabilityLearningQualityLevel:
        if not evidence_sufficient:
            return (
                CapabilityLearningQualityLevel
                .INSUFFICIENT
            )

        if (
            summary_confidence
            >= self.high_quality_threshold
        ):
            return CapabilityLearningQualityLevel.HIGH

        if (
            summary_confidence
            >= self.moderate_quality_threshold
        ):
            return (
                CapabilityLearningQualityLevel
                .MODERATE
            )

        return CapabilityLearningQualityLevel.LOW

    def interpretation(
        self,
        *,
        estimated_success_rate: float,
        unresolved_ratio: float,
        evidence_sufficient: bool,
    ) -> CapabilityLearningInterpretation:
        if not evidence_sufficient:
            return (
                CapabilityLearningInterpretation
                .INSUFFICIENT_EVIDENCE
            )

        if unresolved_ratio >= 0.50:
            return (
                CapabilityLearningInterpretation
                .UNRESOLVED
            )

        if (
            estimated_success_rate
            >= self.positive_threshold
        ):
            return (
                CapabilityLearningInterpretation
                .POSITIVE
            )

        if (
            estimated_success_rate
            < self.negative_threshold
        ):
            return (
                CapabilityLearningInterpretation
                .NEGATIVE
            )

        return CapabilityLearningInterpretation.MIXED


class CapabilityLearningAggregator:
    def __init__(
        self,
        *,
        policy: (
            CapabilityLearningAggregationPolicy
            | None
        ) = None,
    ) -> None:
        self.policy = (
            policy
            or CapabilityLearningAggregationPolicy()
        )

    def summarize(
        self,
        *,
        observations: Iterable[Any],
        capability_id: str,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        tenant_id: str | None = None,
        action: str | None = None,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
    ) -> CapabilityLearningSummary:
        rows = list(observations)
        counts = Counter(
            _read_string(row, "outcome")
            for row in rows
        )

        unsupported = sorted(
            outcome
            for outcome in counts
            if outcome not in SUPPORTED_OUTCOMES
        )

        if unsupported:
            raise ValueError(
                "Unsupported learning outcomes: "
                f"{unsupported}"
            )

        total = len(rows)

        if total == 0:
            return self._empty_summary(
                capability_id=capability_id,
                provider_id=provider_id,
                provider_ref=provider_ref,
                tenant_id=tenant_id,
                action=action,
                window_start=window_start,
                window_end=window_end,
            )

        final_count = sum(
            1
            for row in rows
            if bool(_read(row, "is_final", False))
        )
        retryable_count = sum(
            1
            for row in rows
            if bool(_read(row, "retryable", False))
        )
        evidence_count = sum(
            1
            for row in rows
            if _has_evidence(row)
        )

        confidences = [
            _bounded_float(
                _read(row, "confidence", 0.0)
            )
            for row in rows
        ]

        weights = [
            self._observation_weight(row)
            for row in rows
        ]

        effective_sample_size = sum(weights)

        positive_mass = 0.0
        negative_mass = 0.0
        unresolved_mass = 0.0
        success_value_mass = 0.0

        for row, weight in zip(
            rows,
            weights,
            strict=True,
        ):
            outcome = _read_string(
                row,
                "outcome",
            )

            if outcome == "verified":
                positive_mass += weight
                success_value_mass += weight
            elif outcome == "partially_verified":
                positive_mass += (
                    weight
                    * self.policy.partial_success_value
                )
                unresolved_mass += (
                    weight
                    * (
                        1.0
                        - self.policy
                        .partial_success_value
                    )
                )
                success_value_mass += (
                    weight
                    * self.policy.partial_success_value
                )
            elif outcome == "failed":
                negative_mass += weight
            else:
                unresolved_mass += weight

        total_weight = sum(weights)

        estimated_success_rate = (
            success_value_mass / total_weight
            if total_weight > 0.0
            else 0.0
        )

        average_confidence = (
            sum(confidences) / total
        )
        evidence_coverage = (
            evidence_count / total
        )
        finality_ratio = final_count / total

        sample_confidence = min(
            effective_sample_size
            / self.policy
            .minimum_effective_sample_size,
            1.0,
        )

        # Geometric mean prevents one strong dimension from hiding a
        # weak dimension. If any required quality signal is zero,
        # overall summary confidence is zero.
        quality_product = (
            average_confidence
            * evidence_coverage
            * finality_ratio
            * sample_confidence
        )
        summary_confidence = (
            quality_product ** 0.25
            if quality_product > 0.0
            else 0.0
        )

        evidence_sufficient = (
            effective_sample_size
            >= self.policy
            .minimum_effective_sample_size
        )

        unresolved_ratio = (
            unresolved_mass / total_weight
            if total_weight > 0.0
            else 1.0
        )

        dominant_outcome = _dominant_outcome(
            counts
        )

        quality_level = self.policy.quality_level(
            summary_confidence=summary_confidence,
            evidence_sufficient=evidence_sufficient,
        )

        interpretation = (
            self.policy.interpretation(
                estimated_success_rate=(
                    estimated_success_rate
                ),
                unresolved_ratio=unresolved_ratio,
                evidence_sufficient=(
                    evidence_sufficient
                ),
            )
        )

        return CapabilityLearningSummary(
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
            tenant_id=tenant_id,
            action=action,
            window_start=_aware_or_none(
                window_start
            ),
            window_end=_aware_or_none(
                window_end
            ),
            total_observations=total,
            final_observations=final_count,
            retryable_observations=(
                retryable_count
            ),
            observations_with_evidence=(
                evidence_count
            ),
            verified=counts["verified"],
            partially_verified=counts[
                "partially_verified"
            ],
            failed=counts["failed"],
            inconclusive=counts[
                "inconclusive"
            ],
            not_verifiable=counts[
                "not_verifiable"
            ],
            average_confidence=(
                _bounded_float(
                    average_confidence
                )
            ),
            evidence_coverage=(
                _bounded_float(
                    evidence_coverage
                )
            ),
            finality_ratio=(
                _bounded_float(finality_ratio)
            ),
            effective_sample_size=(
                effective_sample_size
            ),
            weighted_positive_mass=(
                positive_mass
            ),
            weighted_negative_mass=(
                negative_mass
            ),
            weighted_unresolved_mass=(
                unresolved_mass
            ),
            estimated_success_rate=(
                _bounded_float(
                    estimated_success_rate
                )
            ),
            summary_confidence=(
                _bounded_float(
                    summary_confidence
                )
            ),
            minimum_effective_sample_size=(
                self.policy
                .minimum_effective_sample_size
            ),
            evidence_sufficient=(
                evidence_sufficient
            ),
            dominant_outcome=dominant_outcome,
            quality_level=quality_level,
            interpretation=interpretation,
        )

    def _observation_weight(
        self,
        row: Any,
    ) -> float:
        confidence = _bounded_float(
            _read(row, "confidence", 0.0)
        )

        finality_weight = (
            1.0
            if bool(_read(row, "is_final", False))
            else self.policy.non_final_weight
        )

        evidence_weight = (
            1.0
            if _has_evidence(row)
            else self.policy.missing_evidence_weight
        )

        return (
            confidence
            * finality_weight
            * evidence_weight
        )

    def _empty_summary(
        self,
        *,
        capability_id: str,
        provider_id: str | None,
        provider_ref: str | None,
        tenant_id: str | None,
        action: str | None,
        window_start: datetime | None,
        window_end: datetime | None,
    ) -> CapabilityLearningSummary:
        return CapabilityLearningSummary(
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
            tenant_id=tenant_id,
            action=action,
            window_start=_aware_or_none(
                window_start
            ),
            window_end=_aware_or_none(
                window_end
            ),
            total_observations=0,
            final_observations=0,
            retryable_observations=0,
            observations_with_evidence=0,
            verified=0,
            partially_verified=0,
            failed=0,
            inconclusive=0,
            not_verifiable=0,
            average_confidence=0.0,
            evidence_coverage=0.0,
            finality_ratio=0.0,
            effective_sample_size=0.0,
            weighted_positive_mass=0.0,
            weighted_negative_mass=0.0,
            weighted_unresolved_mass=0.0,
            estimated_success_rate=0.0,
            summary_confidence=0.0,
            minimum_effective_sample_size=(
                self.policy
                .minimum_effective_sample_size
            ),
            evidence_sufficient=False,
            dominant_outcome=None,
            quality_level=(
                CapabilityLearningQualityLevel
                .INSUFFICIENT
            ),
            interpretation=(
                CapabilityLearningInterpretation
                .INSUFFICIENT_EVIDENCE
            ),
        )


def _read(
    row: Any,
    key: str,
    default: Any = None,
) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)

    return getattr(row, key, default)


def _read_string(
    row: Any,
    key: str,
) -> str:
    value = _read(row, key)

    if value is None:
        raise ValueError(
            f"{key} is required"
        )

    return str(
        getattr(value, "value", value)
    )


def _has_evidence(row: Any) -> bool:
    summary = _read(
        row,
        "evidence_summary_json",
        None,
    )

    if summary is None:
        summary = _read(
            row,
            "evidence_summary",
            {},
        )

    if not isinstance(summary, dict):
        return False

    count = summary.get("count")

    if isinstance(count, int):
        return count > 0

    items = summary.get("items")

    return (
        isinstance(items, list)
        and len(items) > 0
    )


def _bounded_float(value: Any) -> float:
    resolved = float(value)

    if resolved <= 0.0:
        return 0.0

    if resolved >= 1.0:
        return 1.0

    return resolved


def _dominant_outcome(
    counts: Counter[str],
) -> str | None:
    if not counts:
        return None

    maximum = max(counts.values())
    leaders = sorted(
        outcome
        for outcome, count in counts.items()
        if count == maximum
    )

    return leaders[0]


def _aware_or_none(
    value: datetime | None,
) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value


__all__ = [
    "CapabilityLearningAggregationPolicy",
    "CapabilityLearningAggregator",
    "CapabilityLearningInterpretation",
    "CapabilityLearningQualityLevel",
    "CapabilityLearningSummary",
    "SUPPORTED_OUTCOMES",
]
