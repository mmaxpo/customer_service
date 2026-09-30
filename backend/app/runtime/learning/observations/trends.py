from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.runtime.learning.observations.aggregation import (
    BusinessLearningInterpretation,
    BusinessLearningSummary,
    SUPPORTED_RESULTS,
)


class BusinessLearningTrendDirection(StrEnum):
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    CONTRADICTORY = "contradictory"
    INSUFFICIENT_EVIDENCE = (
        "insufficient_evidence"
    )


class BusinessLearningStabilityLevel(StrEnum):
    STABLE = "stable"
    VARIABLE = "variable"
    UNSTABLE = "unstable"
    INSUFFICIENT = "insufficient"


class BusinessLearningAdvisoryStatus(StrEnum):
    TRUST = "trust"
    WATCH = "watch"
    REVIEW = "review"
    INSUFFICIENT_EVIDENCE = (
        "insufficient_evidence"
    )


class BusinessLearningTrendReport(BaseModel):
    """
    Read-only comparison of two adjacent business
    learning windows.

    The report does not modify planning, workflows,
    routing, learned policy, or runtime behavior.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    tenant_id: str | None = None
    objective_namespace: str
    objective_type: str
    decision: str

    historical: BusinessLearningSummary
    recent: BusinessLearningSummary

    historical_evidence_sufficient: bool
    recent_evidence_sufficient: bool
    comparison_evidence_sufficient: bool

    success_rate_delta: float = Field(
        ge=-1.0,
        le=1.0,
    )
    failure_rate_delta: float = Field(
        ge=-1.0,
        le=1.0,
    )
    confidence_delta: float = Field(
        ge=-1.0,
        le=1.0,
    )
    effective_sample_delta: float

    result_distribution_divergence: float = Field(
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
    dominant_result_changed: bool
    direct_interpretation_conflict: bool

    trend_direction: BusinessLearningTrendDirection
    stability_level: BusinessLearningStabilityLevel
    advisory_status: BusinessLearningAdvisoryStatus

    explanation: str


class BusinessLearningTrendPolicy:
    """
    Deterministic interpretation policy for adjacent
    business-learning windows.
    """

    def __init__(
        self,
        *,
        meaningful_success_delta: float = 0.10,
        meaningful_failure_delta: float = 0.10,
        contradiction_threshold: float = 0.60,
        stable_score_threshold: float = 0.80,
        variable_score_threshold: float = 0.50,
        success_delta_weight: float = 0.30,
        failure_delta_weight: float = 0.20,
        distribution_divergence_weight: float = 0.30,
        contradiction_weight: float = 0.20,
    ) -> None:
        for name, value in (
            (
                "meaningful_success_delta",
                meaningful_success_delta,
            ),
            (
                "meaningful_failure_delta",
                meaningful_failure_delta,
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
                "failure_delta_weight",
                failure_delta_weight,
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
            failure_delta_weight,
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
        self.meaningful_failure_delta = (
            meaningful_failure_delta
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
        self.failure_delta_weight = (
            failure_delta_weight
        )
        self.distribution_divergence_weight = (
            distribution_divergence_weight
        )
        self.contradiction_weight = (
            contradiction_weight
        )


class BusinessLearningTrendAnalyzer:
    def __init__(
        self,
        *,
        policy: (
            BusinessLearningTrendPolicy
            | None
        ) = None,
    ) -> None:
        self.policy = (
            policy
            or BusinessLearningTrendPolicy()
        )

    def compare(
        self,
        *,
        historical: BusinessLearningSummary,
        recent: BusinessLearningSummary,
    ) -> BusinessLearningTrendReport:
        self._require_same_scope(
            historical=historical,
            recent=recent,
        )
        self._require_adjacent_windows(
            historical=historical,
            recent=recent,
        )

        success_delta = (
            recent.estimated_success_rate
            - historical.estimated_success_rate
        )
        failure_delta = (
            recent.estimated_failure_rate
            - historical.estimated_failure_rate
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
            _result_distribution_divergence(
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
            historical.dominant_result
            != recent.dominant_result
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
            failure_delta=failure_delta,
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
            failure_delta=failure_delta,
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

        return BusinessLearningTrendReport(
            tenant_id=historical.tenant_id,
            objective_namespace=(
                historical.objective_namespace
            ),
            objective_type=(
                historical.objective_type
            ),
            decision=historical.decision,
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
            failure_rate_delta=failure_delta,
            confidence_delta=confidence_delta,
            effective_sample_delta=(
                effective_sample_delta
            ),
            result_distribution_divergence=(
                divergence
            ),
            contradiction_score=(
                contradiction_score
            ),
            stability_score=stability_score,
            interpretation_changed=(
                interpretation_changed
            ),
            dominant_result_changed=(
                dominant_changed
            ),
            direct_interpretation_conflict=(
                direct_conflict
            ),
            trend_direction=trend_direction,
            stability_level=stability_level,
            advisory_status=advisory_status,
            explanation=_build_explanation(
                trend_direction=trend_direction,
                stability_level=stability_level,
                success_delta=success_delta,
                failure_delta=failure_delta,
                divergence=divergence,
                contradiction_score=(
                    contradiction_score
                ),
            ),
        )

    @staticmethod
    def _require_same_scope(
        *,
        historical: BusinessLearningSummary,
        recent: BusinessLearningSummary,
    ) -> None:
        if _scope_tuple(
            historical
        ) != _scope_tuple(recent):
            raise ValueError(
                "Business learning trend summaries "
                "must have the same scope"
            )

    @staticmethod
    def _require_adjacent_windows(
        *,
        historical: BusinessLearningSummary,
        recent: BusinessLearningSummary,
    ) -> None:
        if (
            historical.window_start is None
            or historical.window_end is None
            or recent.window_start is None
            or recent.window_end is None
        ):
            raise ValueError(
                "Business learning trend summaries "
                "require bounded windows"
            )

        if (
            historical.window_start
            >= historical.window_end
            or recent.window_start
            >= recent.window_end
        ):
            raise ValueError(
                "Business learning trend windows "
                "must have positive duration"
            )

        if (
            historical.window_end
            != recent.window_start
        ):
            raise ValueError(
                "Business learning trend windows "
                "must be adjacent and non-overlapping"
            )

    def _contradiction_score(
        self,
        *,
        historical: BusinessLearningSummary,
        recent: BusinessLearningSummary,
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
                historical.dominant_result,
                recent.dominant_result,
            }
            == {"achieved", "failed"}
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
        failure_delta: float,
        divergence: float,
        contradiction_score: float,
        comparison_sufficient: bool,
    ) -> float:
        if not comparison_sufficient:
            return 0.0

        instability = (
            self.policy.success_delta_weight
            * abs(success_delta)
            + self.policy.failure_delta_weight
            * abs(failure_delta)
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
        failure_delta: float,
        contradiction_score: float,
        comparison_sufficient: bool,
    ) -> BusinessLearningTrendDirection:
        if not comparison_sufficient:
            return (
                BusinessLearningTrendDirection
                .INSUFFICIENT_EVIDENCE
            )

        if (
            contradiction_score
            >= self.policy
            .contradiction_threshold
        ):
            return (
                BusinessLearningTrendDirection
                .CONTRADICTORY
            )

        improving = (
            success_delta
            >= self.policy
            .meaningful_success_delta
            or failure_delta
            <= -self.policy
            .meaningful_failure_delta
        )

        declining = (
            success_delta
            <= -self.policy
            .meaningful_success_delta
            or failure_delta
            >= self.policy
            .meaningful_failure_delta
        )

        if improving and declining:
            return (
                BusinessLearningTrendDirection
                .CONTRADICTORY
            )

        if improving:
            return (
                BusinessLearningTrendDirection
                .IMPROVING
            )

        if declining:
            return (
                BusinessLearningTrendDirection
                .DECLINING
            )

        return (
            BusinessLearningTrendDirection.STABLE
        )

    def _stability_level(
        self,
        *,
        stability_score: float,
        comparison_sufficient: bool,
    ) -> BusinessLearningStabilityLevel:
        if not comparison_sufficient:
            return (
                BusinessLearningStabilityLevel
                .INSUFFICIENT
            )

        if (
            stability_score
            >= self.policy.stable_score_threshold
        ):
            return (
                BusinessLearningStabilityLevel
                .STABLE
            )

        if (
            stability_score
            >= self.policy.variable_score_threshold
        ):
            return (
                BusinessLearningStabilityLevel
                .VARIABLE
            )

        return (
            BusinessLearningStabilityLevel
            .UNSTABLE
        )

    @staticmethod
    def _advisory_status(
        *,
        trend_direction: (
            BusinessLearningTrendDirection
        ),
        stability_level: (
            BusinessLearningStabilityLevel
        ),
        comparison_sufficient: bool,
    ) -> BusinessLearningAdvisoryStatus:
        if not comparison_sufficient:
            return (
                BusinessLearningAdvisoryStatus
                .INSUFFICIENT_EVIDENCE
            )

        if (
            trend_direction
            == BusinessLearningTrendDirection
            .CONTRADICTORY
            or stability_level
            == BusinessLearningStabilityLevel
            .UNSTABLE
        ):
            return (
                BusinessLearningAdvisoryStatus
                .REVIEW
            )

        if (
            trend_direction
            == BusinessLearningTrendDirection
            .STABLE
            and stability_level
            == BusinessLearningStabilityLevel
            .STABLE
        ):
            return (
                BusinessLearningAdvisoryStatus
                .TRUST
            )

        return (
            BusinessLearningAdvisoryStatus.WATCH
        )


def _scope_tuple(
    summary: BusinessLearningSummary,
) -> tuple[
    str | None,
    str,
    str,
    str,
]:
    return (
        summary.tenant_id,
        summary.objective_namespace,
        summary.objective_type,
        summary.decision,
    )


def _result_distribution_divergence(
    *,
    historical: BusinessLearningSummary,
    recent: BusinessLearningSummary,
) -> float:
    historical_total = (
        historical.total_observations
    )
    recent_total = recent.total_observations

    if (
        historical_total == 0
        and recent_total == 0
    ):
        return 0.0

    distance = 0.0

    for result in SUPPORTED_RESULTS:
        historical_share = (
            getattr(historical, result)
            / historical_total
            if historical_total
            else 0.0
        )
        recent_share = (
            getattr(recent, result)
            / recent_total
            if recent_total
            else 0.0
        )

        distance += abs(
            recent_share - historical_share
        )

    return _bounded(distance / 2.0)


def _is_direct_interpretation_conflict(
    historical: BusinessLearningInterpretation,
    recent: BusinessLearningInterpretation,
) -> bool:
    return {
        historical,
        recent,
    } == {
        BusinessLearningInterpretation.POSITIVE,
        BusinessLearningInterpretation.NEGATIVE,
    }


def _build_explanation(
    *,
    trend_direction: BusinessLearningTrendDirection,
    stability_level: BusinessLearningStabilityLevel,
    success_delta: float,
    failure_delta: float,
    divergence: float,
    contradiction_score: float,
) -> str:
    if (
        trend_direction
        == BusinessLearningTrendDirection
        .INSUFFICIENT_EVIDENCE
    ):
        return (
            "Both adjacent windows require sufficient "
            "evidence before a business trend can be "
            "interpreted."
        )

    return (
        "Business objective evidence is "
        f"{trend_direction.value} with "
        f"{stability_level.value} stability; "
        f"success delta={success_delta:.3f}, "
        f"failure delta={failure_delta:.3f}, "
        f"distribution divergence={divergence:.3f}, "
        f"contradiction score="
        f"{contradiction_score:.3f}."
    )


def _bounded(
    value: float,
) -> float:
    return min(1.0, max(0.0, value))


__all__ = [
    "BusinessLearningAdvisoryStatus",
    "BusinessLearningStabilityLevel",
    "BusinessLearningTrendAnalyzer",
    "BusinessLearningTrendDirection",
    "BusinessLearningTrendPolicy",
    "BusinessLearningTrendReport",
]
