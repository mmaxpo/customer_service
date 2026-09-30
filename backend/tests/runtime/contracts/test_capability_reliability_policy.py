import pytest

from app.runtime.capabilities.execution.performance.reliability import (
    CapabilityReliabilityPolicy,
    CapabilityReliabilityRecommendation,
)


def test_reliability_policy_requires_minimum_evidence():
    policy = CapabilityReliabilityPolicy(
        minimum_attempts=10,
    )

    assert policy.recommend(
        attempts=9,
        success_rate=1.0,
    ) == (
        CapabilityReliabilityRecommendation
        .INSUFFICIENT_EVIDENCE
    )


@pytest.mark.parametrize(
    ("success_rate", "expected"),
    [
        (
            0.98,
            CapabilityReliabilityRecommendation.HEALTHY,
        ),
        (
            0.95,
            CapabilityReliabilityRecommendation.DEGRADED,
        ),
        (
            0.89,
            CapabilityReliabilityRecommendation.UNHEALTHY,
        ),
    ],
)
def test_reliability_policy_classifies_sufficient_evidence(
    success_rate,
    expected,
):
    policy = CapabilityReliabilityPolicy(
        minimum_attempts=10,
    )

    assert policy.recommend(
        attempts=10,
        success_rate=success_rate,
    ) == expected


def test_reliability_policy_validates_thresholds():
    with pytest.raises(
        ValueError,
        match="minimum_attempts",
    ):
        CapabilityReliabilityPolicy(
            minimum_attempts=0,
        )

    with pytest.raises(
        ValueError,
        match="cannot exceed",
    ):
        CapabilityReliabilityPolicy(
            healthy_success_rate=0.90,
            degraded_success_rate=0.95,
        )
