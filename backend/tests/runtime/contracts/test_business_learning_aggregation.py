from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.runtime.learning import (
    BusinessLearningAggregationPolicy,
    BusinessLearningAggregator,
    BusinessLearningEvidenceLevel,
    BusinessLearningInterpretation,
)


def observation(
    *,
    result: str,
    confidence: float = 1.0,
    is_final: bool = True,
    retryable: bool = False,
    evidence_count: int = 1,
    operations: int = 1,
    achieved_operations: int = 0,
    failed_operations: int = 0,
    pending_operations: int = 0,
    unknown_operations: int = 0,
    not_executed_operations: int = 0,
):
    return SimpleNamespace(
        result=result,
        confidence=confidence,
        is_final=is_final,
        retryable=retryable,
        operation_count=operations,
        achieved_operation_count=(
            achieved_operations
        ),
        failed_operation_count=(
            failed_operations
        ),
        pending_operation_count=(
            pending_operations
        ),
        unknown_operation_count=(
            unknown_operations
        ),
        not_executed_operation_count=(
            not_executed_operations
        ),
        evidence_summary_json={
            "count": evidence_count,
            "items": [],
        },
    )


def summarize(
    rows,
    *,
    minimum_effective_sample_size=1.0,
):
    return BusinessLearningAggregator(
        policy=(
            BusinessLearningAggregationPolicy(
                minimum_effective_sample_size=(
                    minimum_effective_sample_size
                )
            )
        )
    ).summarize(
        observations=rows,
        objective_namespace=(
            "customer_service.support"
        ),
        objective_type="multi_operation",
        decision="approved",
    )


def test_achieved_results_are_positive():
    summary = summarize(
        [
            observation(
                result="achieved",
                achieved_operations=1,
            ),
            observation(
                result="achieved",
                achieved_operations=1,
            ),
        ]
    )

    assert summary.achieved == 2
    assert summary.estimated_success_rate == 1.0
    assert summary.estimated_failure_rate == 0.0
    assert summary.interpretation == (
        BusinessLearningInterpretation.POSITIVE
    )


def test_partial_achievement_contributes_partial_success():
    summary = summarize(
        [
            observation(
                result="partially_achieved",
                achieved_operations=1,
                pending_operations=1,
                operations=2,
            ),
            observation(
                result="achieved",
                achieved_operations=1,
            ),
        ]
    )

    assert summary.partially_achieved == 1
    assert summary.weighted_success_mass == 1.5
    assert summary.weighted_unresolved_mass == 0.5
    assert summary.estimated_success_rate == 0.75


def test_failed_results_are_negative():
    summary = summarize(
        [
            observation(
                result="failed",
                failed_operations=1,
            ),
            observation(
                result="failed",
                failed_operations=1,
            ),
        ]
    )

    assert summary.failed == 2
    assert summary.estimated_failure_rate == 1.0
    assert summary.interpretation == (
        BusinessLearningInterpretation.NEGATIVE
    )


def test_progressing_and_inconclusive_are_unresolved():
    summary = summarize(
        [
            observation(
                result="progressing",
                pending_operations=1,
            ),
            observation(
                result="inconclusive",
                unknown_operations=1,
            ),
            observation(
                result="achieved",
                achieved_operations=1,
            ),
        ]
    )

    assert summary.failed == 0
    assert summary.progressing == 1
    assert summary.inconclusive == 1
    assert summary.interpretation == (
        BusinessLearningInterpretation.UNRESOLVED
    )


def test_intentionally_not_executed_is_not_failure():
    summary = summarize(
        [
            observation(
                result=(
                    "intentionally_not_executed"
                ),
                not_executed_operations=1,
            ),
            observation(
                result=(
                    "intentionally_not_executed"
                ),
                not_executed_operations=1,
            ),
            observation(
                result="failed",
                failed_operations=1,
            ),
        ]
    )

    assert (
        summary.intentionally_not_executed
        == 2
    )
    assert summary.failed == 1
    assert summary.interpretation == (
        BusinessLearningInterpretation
        .NOT_EXECUTED
    )


def test_operation_counters_are_aggregated():
    summary = summarize(
        [
            observation(
                result="partially_achieved",
                operations=4,
                achieved_operations=1,
                failed_operations=1,
                pending_operations=1,
                unknown_operations=1,
            ),
            observation(
                result=(
                    "intentionally_not_executed"
                ),
                operations=2,
                not_executed_operations=2,
            ),
        ]
    )

    assert summary.total_operations == 6
    assert summary.achieved_operations == 1
    assert summary.failed_operations == 1
    assert summary.pending_operations == 1
    assert summary.unknown_operations == 1
    assert summary.not_executed_operations == 2


def test_non_final_evidence_is_downweighted():
    summary = BusinessLearningAggregator(
        policy=(
            BusinessLearningAggregationPolicy(
                minimum_effective_sample_size=1.0,
                non_final_weight=0.25,
            )
        )
    ).summarize(
        observations=[
            observation(
                result="progressing",
                is_final=False,
                retryable=True,
            ),
            observation(
                result="achieved",
            ),
        ],
        objective_namespace=(
            "customer_service.support"
        ),
        objective_type="multi_operation",
        decision="approved",
    )

    assert summary.retryable_observations == 1
    assert summary.final_observations == 1
    assert summary.effective_sample_size == 1.25
    assert summary.weighted_success_mass == 1.0
    assert summary.weighted_unresolved_mass == 0.25


def test_missing_evidence_reduces_effective_sample():
    summary = BusinessLearningAggregator(
        policy=(
            BusinessLearningAggregationPolicy(
                minimum_effective_sample_size=2.0,
                missing_evidence_weight=0.5,
            )
        )
    ).summarize(
        observations=[
            observation(
                result="achieved",
                evidence_count=1,
            ),
            observation(
                result="achieved",
                evidence_count=0,
            ),
        ],
        objective_namespace=(
            "customer_service.support"
        ),
        objective_type="multi_operation",
        decision="approved",
    )

    assert summary.evidence_coverage == 0.5
    assert summary.effective_sample_size == 1.5
    assert summary.evidence_sufficient is False
    assert summary.evidence_level == (
        BusinessLearningEvidenceLevel
        .INSUFFICIENT
    )


def test_empty_summary_is_safe():
    now = datetime.now(timezone.utc)

    summary = (
        BusinessLearningAggregator()
        .summarize(
            observations=[],
            objective_namespace=(
                "customer_service.support"
            ),
            objective_type="multi_operation",
            decision="approved",
            window_start=now,
            window_end=now,
        )
    )

    assert summary.total_observations == 0
    assert summary.dominant_result is None
    assert summary.evidence_sufficient is False
    assert summary.interpretation == (
        BusinessLearningInterpretation
        .INSUFFICIENT_EVIDENCE
    )


def test_unknown_result_is_rejected():
    with pytest.raises(
        ValueError,
        match=(
            "Unsupported business learning results"
        ),
    ):
        summarize(
            [
                observation(
                    result="unknown"
                )
            ]
        )


@pytest.mark.parametrize(
    ("keyword", "value"),
    [
        (
            "minimum_effective_sample_size",
            0.0,
        ),
        ("high_evidence_threshold", 1.1),
        ("non_final_weight", -0.1),
        ("missing_evidence_weight", 1.1),
    ],
)
def test_invalid_policy_values_are_rejected(
    keyword,
    value,
):
    with pytest.raises(ValueError):
        BusinessLearningAggregationPolicy(
            **{keyword: value}
        )
