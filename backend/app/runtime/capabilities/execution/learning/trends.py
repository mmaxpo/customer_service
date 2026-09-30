from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.runtime.capabilities.execution.learning.aggregation import (
    CapabilityLearningInterpretation,
    CapabilityLearningSummary,
    SUPPORTED_OUTCOMES,
)


class CapabilityLearningTrendDirection(StrEnum):
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    CONTRADICTORY = "contradictory"
    INSUFFICIENT_EVIDENCE = (
        "insufficient_evidence"
    )


class CapabilityLearningStabilityLevel(StrEnum):
    STABLE = "stable"
    VARIABLE = "variable"
    UNSTABLE = "unstable"
    INSUFFICIENT = "insufficient"


class CapabilityLearningAdvisoryStatus(StrEnum):
    TRUST = "trust"
    WATCH = "watch"
    REVIEW = "review"
    INSUFFICIENT_EVIDENCE = (
        "insufficient_evidence"
    )


class CapabilityLearningTrendReport(BaseModel):
    """
    Advisory comparison of two non-overlapping learning windows.

    The report does not modify provider selection, traffic allocation,
    provider health, learned rules, or runtime policy.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    capability_id: str
    provider_id: str | None = None
    provider_ref: str | None = None
    tenant_id: str | None = None
    action: str | None = None

    historical: CapabilityLearningSummary
    recent: CapabilityLearningSummary

    historical_evidence_sufficient: bool
    recent_evidence_sufficient: bool
    comparison_evidence_sufficient: bool

    success_rate_delta: float = Field(
        ge=-1.0,
        le=1.0,
    )
    confidence_delta: float = Field(
        ge=-1.0,
        le=1.0,
    )
    effective_sample_delta: float

    outcome_distribution_divergence: float = Field(
        ge=0.0,
        le=1.0,
    )
    contradiction_score: float = Field(
        ge=0.0,
        le=1.0,
    )
    stability_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    interpretation_changed: bool
    dominant_outcome_changed: bool
    direct_interpretation_conflict: bool

    trend_direction: CapabilityLearningTrendDirection
    stability_level: CapabilityLearningStabilityLevel
    advisory_status: CapabilityLearningAdvisoryStatus

    explanation: str


class CapabilityLearningTrendPolicy:
    """
    Deterministic interpretation policy for two-window comparison.

    Contradiction and stability are intentionally advisory. They are not
    connected to runtime policy or provider scoring.
    """

    def __init__(
        self,
        *,
        meaningful_success_delta: float = 0.10,
        contradiction_threshold: float = 0.60,
        stable_score_threshold: float = 0.80,
        variable_score_threshold: float = 0.50,
        success_delta_weight: float = 0.40,
        distribution_divergence_weight: float = 0.35,
        contradiction_weight: float = 0.25,
    ) -> None:
        for name, value in (
            (
                "meaningful_success_delta",
                meaningful_success_delta,
            ),
            (
                "contradiction_threshold",
                contradiction_threshold,
            ),
            (
                "stable_score_threshold",
                stable_score_threshold,
            ),
            (
                "variable_score_threshold",
                variable_score_threshold,
            ),
            (
                "success_delta_weight",
                success_delta_weight,
            ),
            (
                "distribution_divergence_weight",
                distribution_divergence_weight,
            ),
            (
                "contradiction_weight",
                contradiction_weight,
            ),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1"
                )

        if (
            variable_score_threshold
            > stable_score_threshold
        ):
            raise ValueError(
                "variable_score_threshold cannot "
                "exceed stable_score_threshold"
            )

        weights = (
            success_delta_weight,
            distribution_divergence_weight,
            contradiction_weight,
        )

        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError(
                "trend weights must sum to 1.0"
            )

        self.meaningful_success_delta = (
            meaningful_success_delta
        )
        self.contradiction_threshold = (
            contradiction_threshold
        )
        self.stable_score_threshold = (
            stable_score_threshold
        )
        self.variable_score_threshold = (
            variable_score_threshold
        )
        self.success_delta_weight = (
            success_delta_weight
        )
        self.distribution_divergence_weight = (
            distribution_divergence_weight
        )
        self.contradiction_weight = (
            contradiction_weight
        )


class CapabilityLearningTrendAnalyzer:
    def __init__(
        self,
        *,
        policy: (
            CapabilityLearningTrendPolicy
            | None
        ) = None,
    ) -> None:
        self.policy = (
            policy
            or CapabilityLearningTrendPolicy()
        )

    def compare(
        self,
        *,
        historical: CapabilityLearningSummary,
        recent: CapabilityLearningSummary,
    ) -> CapabilityLearningTrendReport:
        self._require_same_scope(
            historical=historical,
            recent=recent,
        )
        self._require_non_overlapping_windows(
            historical=historical,
            recent=recent,
        )

        success_delta = (
            recent.estimated_success_rate
            - historical.estimated_success_rate
        )
        confidence_delta = (
            recent.summary_confidence
            - historical.summary_confidence
        )
        effective_sample_delta = (
            recent.effective_sample_size
            - historical.effective_sample_size
        )

        divergence = (
            _outcome_distribution_divergence(
                historical=historical,
                recent=recent,
            )
        )

        direct_conflict = (
            _is_direct_interpretation_conflict(
                historical.interpretation,
                recent.interpretation,
            )
        )

        interpretation_changed = (
            historical.interpretation
            != recent.interpretation
        )
        dominant_changed = (
            historical.dominant_outcome
            != recent.dominant_outcome
        )

        contradiction_score = (
            self._contradiction_score(
                historical=historical,
                recent=recent,
                divergence=divergence,
                direct_conflict=direct_conflict,
                dominant_changed=dominant_changed,
            )
        )

        comparison_sufficient = (
            historical.evidence_sufficient
            and recent.evidence_sufficient
        )

        stability_score = self._stability_score(
            success_delta=success_delta,
            divergence=divergence,
            contradiction_score=(
                contradiction_score
            ),
            comparison_sufficient=(
                comparison_sufficient
            ),
        )

        trend_direction = self._trend_direction(
            success_delta=success_delta,
            contradiction_score=(
                contradiction_score
            ),
            comparison_sufficient=(
                comparison_sufficient
            ),
        )

        stability_level = self._stability_level(
            stability_score=stability_score,
            comparison_sufficient=(
                comparison_sufficient
            ),
        )

        advisory_status = self._advisory_status(
            trend_direction=trend_direction,
            stability_level=stability_level,
            comparison_sufficient=(
                comparison_sufficient
            ),
        )

        explanation = _build_explanation(
            trend_direction=trend_direction,
            stability_level=stability_level,
            success_delta=success_delta,
            divergence=divergence,
            contradiction_score=(
                contradiction_score
            ),
        )

        return CapabilityLearningTrendReport(
            capability_id=historical.capability_id,
            provider_id=historical.provider_id,
            provider_ref=historical.provider_ref,
            tenant_id=historical.tenant_id,
            action=historical.action,
            historical=historical,
            recent=recent,
            historical_evidence_sufficient=(
                historical.evidence_sufficient
            ),
            recent_evidence_sufficient=(
                recent.evidence_sufficient
            ),
            comparison_evidence_sufficient=(
                comparison_sufficient
            ),
            success_rate_delta=success_delta,
            confidence_delta=confidence_delta,
            effective_sample_delta=(
                effective_sample_delta
            ),
            outcome_distribution_divergence=(
                divergence
            ),
            contradiction_score=(
                contradiction_score
            ),
            stability_score=stability_score,
            interpretation_changed=(
                interpretation_changed
            ),
            dominant_outcome_changed=(
                dominant_changed
            ),
            direct_interpretation_conflict=(
                direct_conflict
            ),
            trend_direction=trend_direction,
            stability_level=stability_level,
            advisory_status=advisory_status,
            explanation=explanation,
        )

    @staticmethod
    def _require_same_scope(
        *,
        historical: CapabilityLearningSummary,
        recent: CapabilityLearningSummary,
    ) -> None:
        historical_scope = _scope_tuple(
            historical
        )
        recent_scope = _scope_tuple(recent)

        if historical_scope != recent_scope:
            raise ValueError(
                "Learning trend summaries must "
                "have the same scope"
            )

    @staticmethod
    def _require_non_overlapping_windows(
        *,
        historical: CapabilityLearningSummary,
        recent: CapabilityLearningSummary,
    ) -> None:
        if (
            historical.window_start is None
            or historical.window_end is None
            or recent.window_start is None
            or recent.window_end is None
        ):
            raise ValueError(
                "Learning trend summaries require "
                "bounded windows"
            )

        if (
            historical.window_start
            >= historical.window_end
            or recent.window_start
            >= recent.window_end
        ):
            raise ValueError(
                "Learning trend windows must have "
                "positive duration"
            )

        if historical.window_end > recent.window_start:
            raise ValueError(
                "Learning trend windows must not overlap"
            )

    def _contradiction_score(
        self,
        *,
        historical: CapabilityLearningSummary,
        recent: CapabilityLearningSummary,
        divergence: float,
        direct_conflict: bool,
        dominant_changed: bool,
    ) -> float:
        confidence_support = min(
            historical.summary_confidence,
            recent.summary_confidence,
        )

        direct_conflict_mass = (
            confidence_support
            if direct_conflict
            else 0.0
        )

        dominant_reversal_mass = (
            0.5 * confidence_support
            if dominant_changed
            and {
                historical.dominant_outcome,
                recent.dominant_outcome,
            }
            == {"verified", "failed"}
            else 0.0
        )

        return _bounded(
            max(
                direct_conflict_mass,
                dominant_reversal_mass,
                divergence * confidence_support,
            )
        )

    def _stability_score(
        self,
        *,
        success_delta: float,
        divergence: float,
        contradiction_score: float,
        comparison_sufficient: bool,
    ) -> float:
        if not comparison_sufficient:
            return 0.0

        instability = (
            self.policy.success_delta_weight
            * abs(success_delta)
            + self.policy
            .distribution_divergence_weight
            * divergence
            + self.policy.contradiction_weight
            * contradiction_score
        )

        return _bounded(1.0 - instability)

    def _trend_direction(
        self,
        *,
        success_delta: float,
        contradiction_score: float,
        comparison_sufficient: bool,
    ) -> CapabilityLearningTrendDirection:
        if not comparison_sufficient:
            return (
                CapabilityLearningTrendDirection
                .INSUFFICIENT_EVIDENCE
            )

        if (
            contradiction_score
            >= self.policy
            .contradiction_threshold
        ):
            return (
                CapabilityLearningTrendDirection
                .CONTRADICTORY
            )

        if (
            success_delta
            >= self.policy
            .meaningful_success_delta
        ):
            return (
                CapabilityLearningTrendDirection
                .IMPROVING
            )

        if (
            success_delta
            <= -self.policy
            .meaningful_success_delta
        ):
            return (
                CapabilityLearningTrendDirection
                .DECLINING
            )

        return CapabilityLearningTrendDirection.STABLE

    def _stability_level(
        self,
        *,
        stability_score: float,
        comparison_sufficient: bool,
    ) -> CapabilityLearningStabilityLevel:
        if not comparison_sufficient:
            return (
                CapabilityLearningStabilityLevel
                .INSUFFICIENT
            )

        if (
            stability_score
            >= self.policy.stable_score_threshold
        ):
            return (
                CapabilityLearningStabilityLevel
                .STABLE
            )

        if (
            stability_score
            >= self.policy.variable_score_threshold
        ):
            return (
                CapabilityLearningStabilityLevel
                .VARIABLE
            )

        return (
            CapabilityLearningStabilityLevel
            .UNSTABLE
        )

    @staticmethod
    def _advisory_status(
        *,
        trend_direction: (
            CapabilityLearningTrendDirection
        ),
        stability_level: (
            CapabilityLearningStabilityLevel
        ),
        comparison_sufficient: bool,
    ) -> CapabilityLearningAdvisoryStatus:
        if not comparison_sufficient:
            return (
                CapabilityLearningAdvisoryStatus
                .INSUFFICIENT_EVIDENCE
            )

        if (
            trend_direction
            == CapabilityLearningTrendDirection
            .CONTRADICTORY
            or stability_level
            == CapabilityLearningStabilityLevel
            .UNSTABLE
        ):
            return (
                CapabilityLearningAdvisoryStatus
                .REVIEW
            )

        if (
            trend_direction
            in {
                CapabilityLearningTrendDirection
                .IMPROVING,
                CapabilityLearningTrendDirection
                .DECLINING,
            }
            or stability_level
            == CapabilityLearningStabilityLevel
            .VARIABLE
        ):
            return (
                CapabilityLearningAdvisoryStatus
                .WATCH
            )

        return CapabilityLearningAdvisoryStatus.TRUST


def _scope_tuple(
    summary: CapabilityLearningSummary,
) -> tuple[
    str,
    str | None,
    str | None,
    str | None,
    str | None,
]:
    return (
        summary.capability_id,
        summary.provider_id,
        summary.provider_ref,
        summary.tenant_id,
        summary.action,
    )


def _outcome_distribution_divergence(
    *,
    historical: CapabilityLearningSummary,
    recent: CapabilityLearningSummary,
) -> float:
    historical_distribution = (
        _outcome_distribution(historical)
    )
    recent_distribution = (
        _outcome_distribution(recent)
    )

    # Total variation distance: 0 means identical distributions;
    # 1 means completely disjoint distributions.
    return _bounded(
        0.5
        * sum(
            abs(
                historical_distribution[outcome]
                - recent_distribution[outcome]
            )
            for outcome in SUPPORTED_OUTCOMES
        )
    )


def _outcome_distribution(
    summary: CapabilityLearningSummary,
) -> dict[str, float]:
    total = summary.total_observations

    if total <= 0:
        return {
            outcome: 0.0
            for outcome in SUPPORTED_OUTCOMES
        }

    return {
        "verified": summary.verified / total,
        "partially_verified": (
            summary.partially_verified / total
        ),
        "failed": summary.failed / total,
        "inconclusive": (
            summary.inconclusive / total
        ),
        "not_verifiable": (
            summary.not_verifiable / total
        ),
    }


def _is_direct_interpretation_conflict(
    historical: CapabilityLearningInterpretation,
    recent: CapabilityLearningInterpretation,
) -> bool:
    return {
        historical,
        recent,
    } == {
        CapabilityLearningInterpretation.POSITIVE,
        CapabilityLearningInterpretation.NEGATIVE,
    }


def _build_explanation(
    *,
    trend_direction: CapabilityLearningTrendDirection,
    stability_level: CapabilityLearningStabilityLevel,
    success_delta: float,
    divergence: float,
    contradiction_score: float,
) -> str:
    return (
        f"Trend is {trend_direction.value}; "
        f"stability is {stability_level.value}; "
        f"success-rate delta is "
        f"{success_delta:+.3f}; "
        f"outcome divergence is "
        f"{divergence:.3f}; "
        f"contradiction score is "
        f"{contradiction_score:.3f}."
    )


def _bounded(value: float) -> float:
    if value <= 0.0:
        return 0.0

    if value >= 1.0:
        return 1.0

    return float(value)


__all__ = [
    "CapabilityLearningAdvisoryStatus",
    "CapabilityLearningStabilityLevel",
    "CapabilityLearningTrendAnalyzer",
    "CapabilityLearningTrendDirection",
    "CapabilityLearningTrendPolicy",
    "CapabilityLearningTrendReport",
]
