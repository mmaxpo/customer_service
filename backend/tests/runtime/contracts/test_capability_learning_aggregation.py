from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.runtime.capabilities.execution.learning import (
    CapabilityLearningAggregationPolicy,
    CapabilityLearningAggregator,
    CapabilityLearningInterpretation,
    CapabilityLearningQualityLevel,
)


def observation(
    *,
    outcome: str,
    confidence: float = 1.0,
    is_final: bool = True,
    retryable: bool = False,
    evidence_count: int = 1,
):
    return SimpleNamespace(
        outcome=outcome,
        confidence=confidence,
        is_final=is_final,
        retryable=retryable,
        evidence_summary_json={
            "count": evidence_count,
            "items": [
                {
                    "kind": "provider_state",
                    "source": "shopify",
                }
                for _ in range(
                    evidence_count
                )
            ],
        },
    )


def test_learning_aggregation_requires_effective_evidence():
    aggregator = CapabilityLearningAggregator(
        policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=3.0
            )
        )
    )

    summary = aggregator.summarize(
        observations=[
            observation(
                outcome="verified",
            ),
            observation(
                outcome="verified",
            ),
        ],
        capability_id=(
            "ecommerce.orders.manage"
        ),
        provider_id="shopify",
        action="refund",
    )

    assert summary.total_observations == 2
    assert summary.verified == 2
    assert summary.effective_sample_size == 2.0
    assert summary.estimated_success_rate == 1.0
    assert summary.evidence_sufficient is False
    assert summary.quality_level == (
        CapabilityLearningQualityLevel
        .INSUFFICIENT
    )
    assert summary.interpretation == (
        CapabilityLearningInterpretation
        .INSUFFICIENT_EVIDENCE
    )


def test_high_quality_positive_evidence_is_interpreted_positive():
    aggregator = CapabilityLearningAggregator(
        policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=3.0
            )
        )
    )

    summary = aggregator.summarize(
        observations=[
            observation(
                outcome="verified",
            ),
            observation(
                outcome="verified",
                confidence=0.9,
            ),
            observation(
                outcome="verified",
                confidence=0.9,
            ),
            observation(
                outcome="failed",
                confidence=0.5,
            ),
        ],
        capability_id=(
            "ecommerce.orders.manage"
        ),
        provider_id="shopify",
        provider_ref="shopify.order_action",
        tenant_id="tenant-a",
        action="refund",
    )

    assert summary.total_observations == 4
    assert summary.verified == 3
    assert summary.failed == 1
    assert summary.evidence_sufficient is True
    assert (
        summary.estimated_success_rate
        > 0.80
    )
    assert summary.quality_level in {
        CapabilityLearningQualityLevel
        .MODERATE,
        CapabilityLearningQualityLevel
        .HIGH,
    }
    assert summary.interpretation == (
        CapabilityLearningInterpretation
        .POSITIVE
    )


def test_non_final_retryable_evidence_is_downweighted():
    aggregator = CapabilityLearningAggregator(
        policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=1.0,
                non_final_weight=0.25,
            )
        )
    )

    summary = aggregator.summarize(
        observations=[
            observation(
                outcome="inconclusive",
                confidence=1.0,
                is_final=False,
                retryable=True,
            ),
            observation(
                outcome="verified",
                confidence=1.0,
                is_final=True,
                retryable=False,
            ),
        ],
        capability_id=(
            "ecommerce.orders.manage"
        ),
        action="refund",
    )

    assert summary.retryable_observations == 1
    assert summary.final_observations == 1
    assert summary.effective_sample_size == 1.25
    assert summary.weighted_positive_mass == 1.0
    assert summary.weighted_unresolved_mass == 0.25
    assert summary.estimated_success_rate == 0.8
    assert summary.interpretation == (
        CapabilityLearningInterpretation
        .POSITIVE
    )


def test_unresolved_majority_is_not_treated_as_failure():
    aggregator = CapabilityLearningAggregator(
        policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=2.0
            )
        )
    )

    summary = aggregator.summarize(
        observations=[
            observation(
                outcome="inconclusive",
            ),
            observation(
                outcome="not_verifiable",
            ),
            observation(
                outcome="verified",
            ),
        ],
        capability_id=(
            "ecommerce.orders.manage"
        ),
    )

    assert summary.failed == 0
    assert summary.weighted_negative_mass == 0.0
    assert summary.weighted_unresolved_mass == 2.0
    assert summary.interpretation == (
        CapabilityLearningInterpretation
        .UNRESOLVED
    )


def test_partial_verification_contributes_partial_success():
    aggregator = CapabilityLearningAggregator(
        policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=2.0,
                partial_success_value=0.5,
            )
        )
    )

    summary = aggregator.summarize(
        observations=[
            observation(
                outcome="partially_verified",
            ),
            observation(
                outcome="verified",
            ),
        ],
        capability_id=(
            "ecommerce.orders.manage"
        ),
    )

    assert summary.partially_verified == 1
    assert summary.weighted_positive_mass == 1.5
    assert summary.weighted_unresolved_mass == 0.5
    assert summary.estimated_success_rate == 0.75


def test_missing_normalized_evidence_reduces_effective_sample():
    aggregator = CapabilityLearningAggregator(
        policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=2.0,
                missing_evidence_weight=0.5,
            )
        )
    )

    summary = aggregator.summarize(
        observations=[
            observation(
                outcome="verified",
                evidence_count=1,
            ),
            observation(
                outcome="verified",
                evidence_count=0,
            ),
        ],
        capability_id=(
            "ecommerce.orders.manage"
        ),
    )

    assert summary.observations_with_evidence == 1
    assert summary.evidence_coverage == 0.5
    assert summary.effective_sample_size == 1.5
    assert summary.evidence_sufficient is False


def test_empty_summary_is_safe_and_insufficient():
    now = datetime.now(timezone.utc)

    summary = (
        CapabilityLearningAggregator()
        .summarize(
            observations=[],
            capability_id=(
                "ecommerce.orders.manage"
            ),
            window_start=now,
            window_end=now,
        )
    )

    assert summary.total_observations == 0
    assert summary.summary_confidence == 0.0
    assert summary.dominant_outcome is None
    assert summary.evidence_sufficient is False
    assert summary.interpretation == (
        CapabilityLearningInterpretation
        .INSUFFICIENT_EVIDENCE
    )


def test_unknown_outcome_is_rejected():
    with pytest.raises(
        ValueError,
        match="Unsupported learning outcomes",
    ):
        (
            CapabilityLearningAggregator()
            .summarize(
                observations=[
                    observation(
                        outcome="unknown"
                    )
                ],
                capability_id=(
                    "ecommerce.orders.manage"
                ),
            )
        )


@pytest.mark.parametrize(
    ("keyword", "value"),
    [
        (
            "minimum_effective_sample_size",
            0.0,
        ),
        ("high_quality_threshold", 1.1),
        ("non_final_weight", -0.1),
        ("missing_evidence_weight", 1.1),
    ],
)
def test_invalid_learning_policy_values_are_rejected(
    keyword,
    value,
):
    with pytest.raises(ValueError):
        CapabilityLearningAggregationPolicy(
            **{keyword: value}
        )
