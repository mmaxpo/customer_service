from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


SUPPORTED_RESULTS = (
    "achieved",
    "partially_achieved",
    "progressing",
    "failed",
    "intentionally_not_executed",
    "inconclusive",
)


class BusinessLearningEvidenceLevel(StrEnum):
    INSUFFICIENT = "insufficient"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class BusinessLearningInterpretation(StrEnum):
    POSITIVE = "positive"
    MIXED = "mixed"
    NEGATIVE = "negative"
    UNRESOLVED = "unresolved"
    NOT_EXECUTED = "not_executed"
    INSUFFICIENT_EVIDENCE = (
        "insufficient_evidence"
    )


class BusinessLearningSummary(BaseModel):
    """
    Read-only interpretation of immutable business
    objective evidence.

    This summary does not alter planning, routing,
    workflow policy, or runtime behavior.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    tenant_id: str | None = None
    objective_namespace: str
    objective_type: str
    decision: str

    window_start: datetime | None = None
    window_end: datetime | None = None

    total_observations: int = Field(ge=0)
    final_observations: int = Field(ge=0)
    retryable_observations: int = Field(ge=0)
    observations_with_evidence: int = Field(
        ge=0
    )

    achieved: int = Field(ge=0)
    partially_achieved: int = Field(ge=0)
    progressing: int = Field(ge=0)
    failed: int = Field(ge=0)
    intentionally_not_executed: int = Field(
        ge=0
    )
    inconclusive: int = Field(ge=0)

    total_operations: int = Field(ge=0)
    achieved_operations: int = Field(ge=0)
    failed_operations: int = Field(ge=0)
    pending_operations: int = Field(ge=0)
    unknown_operations: int = Field(ge=0)
    not_executed_operations: int = Field(
        ge=0
    )

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
    weighted_success_mass: float = Field(
        ge=0.0
    )
    weighted_failure_mass: float = Field(
        ge=0.0
    )
    weighted_unresolved_mass: float = Field(
        ge=0.0
    )
    weighted_not_executed_mass: float = Field(
        ge=0.0
    )

    estimated_success_rate: float = Field(
        ge=0.0,
        le=1.0,
    )
    estimated_failure_rate: float = Field(
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

    dominant_result: str | None = None
    evidence_level: BusinessLearningEvidenceLevel
    interpretation: BusinessLearningInterpretation


class BusinessLearningAggregationPolicy:
    def __init__(
        self,
        *,
        minimum_effective_sample_size: float = 5.0,
        high_evidence_threshold: float = 0.80,
        moderate_evidence_threshold: float = 0.55,
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
                "high_evidence_threshold",
                high_evidence_threshold,
            ),
            (
                "moderate_evidence_threshold",
                moderate_evidence_threshold,
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
            moderate_evidence_threshold
            > high_evidence_threshold
        ):
            raise ValueError(
                "moderate_evidence_threshold cannot "
                "exceed high_evidence_threshold"
            )

        if negative_threshold > positive_threshold:
            raise ValueError(
                "negative_threshold cannot exceed "
                "positive_threshold"
            )

        self.minimum_effective_sample_size = (
            minimum_effective_sample_size
        )
        self.high_evidence_threshold = (
            high_evidence_threshold
        )
        self.moderate_evidence_threshold = (
            moderate_evidence_threshold
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

    def evidence_level(
        self,
        *,
        summary_confidence: float,
        evidence_sufficient: bool,
    ) -> BusinessLearningEvidenceLevel:
        if not evidence_sufficient:
            return (
                BusinessLearningEvidenceLevel
                .INSUFFICIENT
            )

        if (
            summary_confidence
            >= self.high_evidence_threshold
        ):
            return BusinessLearningEvidenceLevel.HIGH

        if (
            summary_confidence
            >= self.moderate_evidence_threshold
        ):
            return (
                BusinessLearningEvidenceLevel
                .MODERATE
            )

        return BusinessLearningEvidenceLevel.LOW

    def interpretation(
        self,
        *,
        estimated_success_rate: float,
        estimated_failure_rate: float,
        unresolved_ratio: float,
        not_executed_ratio: float,
        evidence_sufficient: bool,
    ) -> BusinessLearningInterpretation:
        if not evidence_sufficient:
            return (
                BusinessLearningInterpretation
                .INSUFFICIENT_EVIDENCE
            )

        if not_executed_ratio >= 0.50:
            return (
                BusinessLearningInterpretation
                .NOT_EXECUTED
            )

        if unresolved_ratio >= 0.50:
            return (
                BusinessLearningInterpretation
                .UNRESOLVED
            )

        if (
            estimated_success_rate
            >= self.positive_threshold
        ):
            return (
                BusinessLearningInterpretation
                .POSITIVE
            )

        if (
            estimated_failure_rate
            > (
                1.0
                - self.negative_threshold
            )
        ):
            return (
                BusinessLearningInterpretation
                .NEGATIVE
            )

        return BusinessLearningInterpretation.MIXED


class BusinessLearningAggregator:
    def __init__(
        self,
        *,
        policy: (
            BusinessLearningAggregationPolicy
            | None
        ) = None,
    ) -> None:
        self.policy = (
            policy
            or BusinessLearningAggregationPolicy()
        )

    def summarize(
        self,
        *,
        observations: Iterable[Any],
        objective_namespace: str,
        objective_type: str,
        decision: str,
        tenant_id: str | None = None,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
    ) -> BusinessLearningSummary:
        rows = list(observations)

        counts = Counter(
            _read_string(row, "result")
            for row in rows
        )

        unsupported = sorted(
            result
            for result in counts
            if result not in SUPPORTED_RESULTS
        )

        if unsupported:
            raise ValueError(
                "Unsupported business learning "
                f"results: {unsupported}"
            )

        if not rows:
            return self._empty_summary(
                objective_namespace=(
                    objective_namespace
                ),
                objective_type=objective_type,
                decision=decision,
                tenant_id=tenant_id,
                window_start=window_start,
                window_end=window_end,
            )

        total = len(rows)

        final_count = sum(
            1
            for row in rows
            if bool(
                _read(row, "is_final", False)
            )
        )
        retryable_count = sum(
            1
            for row in rows
            if bool(
                _read(row, "retryable", False)
            )
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

        success_mass = 0.0
        failure_mass = 0.0
        unresolved_mass = 0.0
        not_executed_mass = 0.0

        for row, weight in zip(
            rows,
            weights,
            strict=True,
        ):
            result = _read_string(
                row,
                "result",
            )

            if result == "achieved":
                success_mass += weight
            elif result == "partially_achieved":
                success_mass += (
                    weight
                    * self.policy
                    .partial_success_value
                )
                unresolved_mass += (
                    weight
                    * (
                        1.0
                        - self.policy
                        .partial_success_value
                    )
                )
            elif result == "failed":
                failure_mass += weight
            elif (
                result
                == "intentionally_not_executed"
            ):
                not_executed_mass += weight
            else:
                unresolved_mass += weight

        total_weight = sum(weights)

        estimated_success_rate = (
            success_mass / total_weight
            if total_weight
            else 0.0
        )
        estimated_failure_rate = (
            failure_mass / total_weight
            if total_weight
            else 0.0
        )

        evidence_coverage = (
            evidence_count / total
        )
        finality_ratio = final_count / total
        average_confidence = (
            sum(confidences) / total
        )

        effective_sample_size = total_weight

        evidence_sufficient = (
            effective_sample_size
            >= self.policy
            .minimum_effective_sample_size
        )

        summary_confidence = min(
            1.0,
            (
                effective_sample_size
                / self.policy
                .minimum_effective_sample_size
            )
            * average_confidence
            * evidence_coverage,
        )

        unresolved_ratio = (
            unresolved_mass / total_weight
            if total_weight
            else 0.0
        )
        not_executed_ratio = (
            not_executed_mass / total_weight
            if total_weight
            else 0.0
        )

        operation_fields = {
            "total_operations": "operation_count",
            "achieved_operations": (
                "achieved_operation_count"
            ),
            "failed_operations": (
                "failed_operation_count"
            ),
            "pending_operations": (
                "pending_operation_count"
            ),
            "unknown_operations": (
                "unknown_operation_count"
            ),
            "not_executed_operations": (
                "not_executed_operation_count"
            ),
        }

        operation_totals = {
            output_name: sum(
                max(
                    0,
                    int(
                        _read(
                            row,
                            source_name,
                            0,
                        )
                        or 0
                    ),
                )
                for row in rows
            )
            for (
                output_name,
                source_name,
            ) in operation_fields.items()
        }

        dominant_result = (
            counts.most_common(1)[0][0]
            if counts
            else None
        )

        return BusinessLearningSummary(
            tenant_id=tenant_id,
            objective_namespace=(
                objective_namespace
            ),
            objective_type=objective_type,
            decision=decision,
            window_start=window_start,
            window_end=window_end,
            total_observations=total,
            final_observations=final_count,
            retryable_observations=(
                retryable_count
            ),
            observations_with_evidence=(
                evidence_count
            ),
            achieved=counts["achieved"],
            partially_achieved=(
                counts["partially_achieved"]
            ),
            progressing=counts["progressing"],
            failed=counts["failed"],
            intentionally_not_executed=(
                counts[
                    "intentionally_not_executed"
                ]
            ),
            inconclusive=counts["inconclusive"],
            average_confidence=(
                average_confidence
            ),
            evidence_coverage=evidence_coverage,
            finality_ratio=finality_ratio,
            effective_sample_size=(
                effective_sample_size
            ),
            weighted_success_mass=(
                success_mass
            ),
            weighted_failure_mass=(
                failure_mass
            ),
            weighted_unresolved_mass=(
                unresolved_mass
            ),
            weighted_not_executed_mass=(
                not_executed_mass
            ),
            estimated_success_rate=(
                estimated_success_rate
            ),
            estimated_failure_rate=(
                estimated_failure_rate
            ),
            summary_confidence=(
                summary_confidence
            ),
            minimum_effective_sample_size=(
                self.policy
                .minimum_effective_sample_size
            ),
            evidence_sufficient=(
                evidence_sufficient
            ),
            dominant_result=dominant_result,
            evidence_level=(
                self.policy.evidence_level(
                    summary_confidence=(
                        summary_confidence
                    ),
                    evidence_sufficient=(
                        evidence_sufficient
                    ),
                )
            ),
            interpretation=(
                self.policy.interpretation(
                    estimated_success_rate=(
                        estimated_success_rate
                    ),
                    estimated_failure_rate=(
                        estimated_failure_rate
                    ),
                    unresolved_ratio=(
                        unresolved_ratio
                    ),
                    not_executed_ratio=(
                        not_executed_ratio
                    ),
                    evidence_sufficient=(
                        evidence_sufficient
                    ),
                )
            ),
            **operation_totals,
        )

    def _observation_weight(
        self,
        row: Any,
    ) -> float:
        weight = _bounded_float(
            _read(row, "confidence", 0.0)
        )

        if not bool(
            _read(row, "is_final", False)
        ):
            weight *= self.policy.non_final_weight

        if not _has_evidence(row):
            weight *= (
                self.policy.missing_evidence_weight
            )

        return weight

    def _empty_summary(
        self,
        *,
        objective_namespace: str,
        objective_type: str,
        decision: str,
        tenant_id: str | None,
        window_start: datetime | None,
        window_end: datetime | None,
    ) -> BusinessLearningSummary:
        return BusinessLearningSummary(
            tenant_id=tenant_id,
            objective_namespace=(
                objective_namespace
            ),
            objective_type=objective_type,
            decision=decision,
            window_start=window_start,
            window_end=window_end,
            total_observations=0,
            final_observations=0,
            retryable_observations=0,
            observations_with_evidence=0,
            achieved=0,
            partially_achieved=0,
            progressing=0,
            failed=0,
            intentionally_not_executed=0,
            inconclusive=0,
            total_operations=0,
            achieved_operations=0,
            failed_operations=0,
            pending_operations=0,
            unknown_operations=0,
            not_executed_operations=0,
            average_confidence=0.0,
            evidence_coverage=0.0,
            finality_ratio=0.0,
            effective_sample_size=0.0,
            weighted_success_mass=0.0,
            weighted_failure_mass=0.0,
            weighted_unresolved_mass=0.0,
            weighted_not_executed_mass=0.0,
            estimated_success_rate=0.0,
            estimated_failure_rate=0.0,
            summary_confidence=0.0,
            minimum_effective_sample_size=(
                self.policy
                .minimum_effective_sample_size
            ),
            evidence_sufficient=False,
            dominant_result=None,
            evidence_level=(
                BusinessLearningEvidenceLevel
                .INSUFFICIENT
            ),
            interpretation=(
                BusinessLearningInterpretation
                .INSUFFICIENT_EVIDENCE
            ),
        )


def _read(
    row: Any,
    name: str,
    default: Any = None,
) -> Any:
    if isinstance(row, dict):
        return row.get(name, default)

    return getattr(row, name, default)


def _read_string(
    row: Any,
    name: str,
) -> str:
    value = _read(row, name, "")
    return str(value or "").strip()


def _bounded_float(
    value: Any,
) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0

    return min(1.0, max(0.0, parsed))


def _has_evidence(
    row: Any,
) -> bool:
    summary = _read(
        row,
        "evidence_summary_json",
        {},
    )

    if not isinstance(summary, dict):
        return False

    try:
        return int(
            summary.get("count") or 0
        ) > 0
    except (TypeError, ValueError):
        return False


__all__ = [
    "SUPPORTED_RESULTS",
    "BusinessLearningAggregationPolicy",
    "BusinessLearningAggregator",
    "BusinessLearningEvidenceLevel",
    "BusinessLearningInterpretation",
    "BusinessLearningSummary",
]
