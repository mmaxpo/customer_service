from datetime import datetime, timedelta, timezone

import pytest

from app.runtime.capabilities.execution.health.decisions import (
    ProviderHealthDecisionAction,
    ProviderHealthDecisionPolicy,
    ProviderHealthDecisionReason,
    ProviderHealthState,
)
from app.runtime.capabilities.execution.performance.reliability import (
    CapabilityProviderReliabilityReport,
    CapabilityReliabilityRecommendation,
)


NOW = datetime(
    2026,
    7,
    12,
    12,
    0,
    tzinfo=timezone.utc,
)


def report(
    *,
    recommendation=(
        CapabilityReliabilityRecommendation.HEALTHY
    ),
    evidence_sufficient=True,
    attempts=20,
    successes=20,
):
    failures = attempts - successes

    return CapabilityProviderReliabilityReport(
        capability_id="ecommerce.orders.get",
        provider_id="shopify",
        provider_ref="shopify.get_order",
        tenant_id="tenant_1",
        window_start=NOW - timedelta(hours=1),
        window_end=NOW,
        attempts=attempts,
        successes=successes,
        failures=failures,
        timeouts=failures,
        unavailable=0,
        circuit_open=0,
        provider_errors=0,
        other_failures=0,
        fallback_eligible_failures=failures,
        fallback_recoveries=0,
        fallback_invocations=0,
        success_rate=(
            successes / attempts
            if attempts
            else 0.0
        ),
        failure_rate=(
            failures / attempts
            if attempts
            else 0.0
        ),
        timeout_rate=(
            failures / attempts
            if attempts
            else 0.0
        ),
        provider_error_rate=0.0,
        fallback_recovery_rate=0.0,
        average_duration_ms=10.0,
        minimum_attempts=10,
        evidence_sufficient=evidence_sufficient,
        recommendation=recommendation,
    )


def test_insufficient_evidence_never_proposes_transition():
    decision = ProviderHealthDecisionPolicy().decide(
        user_id="user_1",
        report=report(
            recommendation=(
                CapabilityReliabilityRecommendation
                .UNHEALTHY
            ),
            evidence_sufficient=False,
            attempts=5,
            successes=0,
        ),
        qualifying_windows=10,
        evaluated_at=NOW,
    )

    assert decision.action == (
        ProviderHealthDecisionAction.HOLD
    )
    assert decision.current_state == (
        ProviderHealthState.HEALTHY
    )
    assert decision.proposed_state == (
        ProviderHealthState.HEALTHY
    )
    assert decision.reason == (
        ProviderHealthDecisionReason
        .INSUFFICIENT_EVIDENCE
    )


def test_one_degraded_window_does_not_degrade_provider():
    decision = ProviderHealthDecisionPolicy(
        degrade_after_windows=2,
    ).decide(
        user_id="user_1",
        report=report(
            recommendation=(
                CapabilityReliabilityRecommendation
                .DEGRADED
            ),
            successes=19,
        ),
        qualifying_windows=1,
        evaluated_at=NOW,
    )

    assert decision.action == (
        ProviderHealthDecisionAction.HOLD
    )
    assert decision.reason == (
        ProviderHealthDecisionReason
        .DEGRADATION_PENDING
    )


def test_consecutive_degraded_windows_propose_degraded():
    decision = ProviderHealthDecisionPolicy(
        degrade_after_windows=2,
    ).decide(
        user_id="user_1",
        report=report(
            recommendation=(
                CapabilityReliabilityRecommendation
                .DEGRADED
            ),
            successes=19,
        ),
        qualifying_windows=2,
        evaluated_at=NOW,
    )

    assert decision.transition_proposed is True
    assert decision.current_state == (
        ProviderHealthState.HEALTHY
    )
    assert decision.proposed_state == (
        ProviderHealthState.DEGRADED
    )
    assert decision.scope.tenant_id == "tenant_1"


def test_unhealthy_requires_more_consecutive_windows():
    policy = ProviderHealthDecisionPolicy(
        degrade_after_windows=2,
        unhealthy_after_windows=3,
    )

    pending = policy.decide(
        user_id="user_1",
        report=report(
            recommendation=(
                CapabilityReliabilityRecommendation
                .UNHEALTHY
            ),
            successes=10,
        ),
        qualifying_windows=2,
        evaluated_at=NOW,
    )

    confirmed = policy.decide(
        user_id="user_1",
        report=report(
            recommendation=(
                CapabilityReliabilityRecommendation
                .UNHEALTHY
            ),
            successes=10,
        ),
        qualifying_windows=3,
        evaluated_at=NOW,
    )

    assert pending.action == (
        ProviderHealthDecisionAction.HOLD
    )
    assert confirmed.proposed_state == (
        ProviderHealthState.UNHEALTHY
    )


def test_cooldown_blocks_unhealthy_recovery_transition():
    decision = ProviderHealthDecisionPolicy().decide(
        user_id="user_1",
        report=report(),
        current_state=ProviderHealthState.UNHEALTHY,
        qualifying_windows=3,
        cooldown_until=NOW + timedelta(minutes=30),
        evaluated_at=NOW,
    )

    assert decision.action == (
        ProviderHealthDecisionAction.HOLD
    )
    assert decision.reason == (
        ProviderHealthDecisionReason.COOLDOWN_ACTIVE
    )
    assert decision.proposed_state == (
        ProviderHealthState.UNHEALTHY
    )


def test_healthy_window_moves_unhealthy_to_recovering():
    decision = ProviderHealthDecisionPolicy().decide(
        user_id="user_1",
        report=report(),
        current_state=ProviderHealthState.UNHEALTHY,
        qualifying_windows=1,
        cooldown_until=NOW - timedelta(minutes=1),
        evaluated_at=NOW,
    )

    assert decision.transition_proposed is True
    assert decision.proposed_state == (
        ProviderHealthState.RECOVERING
    )
    assert decision.reason == (
        ProviderHealthDecisionReason.RECOVERY_STARTED
    )


def test_recovery_requires_consecutive_healthy_windows():
    policy = ProviderHealthDecisionPolicy(
        recover_after_windows=2,
    )

    pending = policy.decide(
        user_id="user_1",
        report=report(),
        current_state=ProviderHealthState.RECOVERING,
        qualifying_windows=1,
        evaluated_at=NOW,
    )

    confirmed = policy.decide(
        user_id="user_1",
        report=report(),
        current_state=ProviderHealthState.RECOVERING,
        qualifying_windows=2,
        evaluated_at=NOW,
    )

    assert pending.reason == (
        ProviderHealthDecisionReason.RECOVERY_PENDING
    )
    assert confirmed.proposed_state == (
        ProviderHealthState.HEALTHY
    )
    assert confirmed.reason == (
        ProviderHealthDecisionReason
        .RECOVERY_CONFIRMED
    )


def test_unhealthy_evidence_regresses_recovering_provider():
    decision = ProviderHealthDecisionPolicy().decide(
        user_id="user_1",
        report=report(
            recommendation=(
                CapabilityReliabilityRecommendation
                .UNHEALTHY
            ),
            successes=5,
        ),
        current_state=ProviderHealthState.RECOVERING,
        qualifying_windows=1,
        evaluated_at=NOW,
    )

    assert decision.proposed_state == (
        ProviderHealthState.UNHEALTHY
    )
    assert decision.reason == (
        ProviderHealthDecisionReason
        .RECOVERY_REGRESSED
    )


def test_decision_policy_never_mutates_health_registry():
    from app.runtime.capabilities.registry.state import (
        ProviderHealthRegistry,
    )

    registry = ProviderHealthRegistry()

    decision = ProviderHealthDecisionPolicy().decide(
        user_id="user_1",
        report=report(
            recommendation=(
                CapabilityReliabilityRecommendation
                .UNHEALTHY
            ),
            successes=5,
        ),
        qualifying_windows=3,
        evaluated_at=NOW,
    )

    assert decision.proposed_state == (
        ProviderHealthState.UNHEALTHY
    )
    assert registry.is_healthy("shopify") is True


def test_policy_rejects_invalid_window_configuration():
    with pytest.raises(
        ValueError,
        match="degrade_after_windows",
    ):
        ProviderHealthDecisionPolicy(
            degrade_after_windows=0,
        )

    with pytest.raises(
        ValueError,
        match="cannot be lower",
    ):
        ProviderHealthDecisionPolicy(
            degrade_after_windows=3,
            unhealthy_after_windows=2,
        )


def test_report_requires_provider_identity():
    missing_provider = report().model_copy(
        update={"provider_id": None}
    )

    with pytest.raises(
        ValueError,
        match="provider_id is required",
    ):
        ProviderHealthDecisionPolicy().decide(
            user_id="user_1",
            report=missing_provider,
            evaluated_at=NOW,
        )
