from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.runtime.capabilities.execution.learning import (
    CapabilityLearningAdvisoryStatus,
    CapabilityLearningInterpretation,
    CapabilityLearningQualityLevel,
    CapabilityLearningStabilityLevel,
    CapabilityLearningSummary,
    CapabilityLearningTrendDirection,
    CapabilityLearningTrendReport,
    CapabilityLearningTrendService,
)


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


def summary(
    *,
    start,
    end,
):
    return CapabilityLearningSummary(
        capability_id="capability.a",
        provider_id="provider-a",
        provider_ref="provider-a.action",
        tenant_id="tenant-a",
        action="refund",
        window_start=start,
        window_end=end,
        total_observations=5,
        final_observations=5,
        retryable_observations=0,
        observations_with_evidence=5,
        verified=5,
        partially_verified=0,
        failed=0,
        inconclusive=0,
        not_verifiable=0,
        average_confidence=1.0,
        evidence_coverage=1.0,
        finality_ratio=1.0,
        effective_sample_size=5.0,
        weighted_positive_mass=5.0,
        weighted_negative_mass=0.0,
        weighted_unresolved_mass=0.0,
        estimated_success_rate=1.0,
        summary_confidence=1.0,
        minimum_effective_sample_size=5.0,
        evidence_sufficient=True,
        dominant_outcome="verified",
        quality_level=(
            CapabilityLearningQualityLevel.HIGH
        ),
        interpretation=(
            CapabilityLearningInterpretation
            .POSITIVE
        ),
    )


@pytest.mark.asyncio
async def test_learning_trend_route_is_authenticated_and_scoped(
    monkeypatch,
):
    user_id = uuid4()
    captured = {}

    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(days=7)
    historical_start = (
        recent_start - timedelta(days=7)
    )

    async def fake_analyze(
        self,
        **kwargs,
    ):
        captured.update(kwargs)

        historical = summary(
            start=historical_start,
            end=recent_start,
        )
        recent = summary(
            start=recent_start,
            end=now,
        )

        return [
            CapabilityLearningTrendReport(
                capability_id="capability.a",
                provider_id="provider-a",
                provider_ref="provider-a.action",
                tenant_id="tenant-a",
                action="refund",
                historical=historical,
                recent=recent,
                historical_evidence_sufficient=True,
                recent_evidence_sufficient=True,
                comparison_evidence_sufficient=True,
                success_rate_delta=0.0,
                confidence_delta=0.0,
                effective_sample_delta=0.0,
                outcome_distribution_divergence=0.0,
                contradiction_score=0.0,
                stability_score=1.0,
                interpretation_changed=False,
                dominant_outcome_changed=False,
                direct_interpretation_conflict=False,
                trend_direction=(
                    CapabilityLearningTrendDirection
                    .STABLE
                ),
                stability_level=(
                    CapabilityLearningStabilityLevel
                    .STABLE
                ),
                advisory_status=(
                    CapabilityLearningAdvisoryStatus
                    .TRUST
                ),
                explanation="Stable learning evidence.",
            )
        ]

    monkeypatch.setattr(
        CapabilityLearningTrendService,
        "analyze",
        fake_analyze,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/capabilities/"
                "learning-observations/trends",
                params={
                    "tenant_id": "tenant-a",
                    "capability_id": "capability.a",
                    "provider_id": "provider-a",
                    "provider_ref": (
                        "provider-a.action"
                    ),
                    "action": "refund",
                    "window_hours": 168,
                    "minimum_effective_sample_size": 4,
                    "meaningful_success_delta": 0.15,
                    "contradiction_threshold": 0.7,
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1
        assert (
            body[0]["trend_direction"]
            == "stable"
        )
        assert (
            body[0]["stability_level"]
            == "stable"
        )
        assert (
            body[0]["advisory_status"]
            == "trust"
        )

        assert captured["user_id"] == user_id
        assert captured["tenant_id"] == (
            "tenant-a"
        )
        assert captured["capability_id"] == (
            "capability.a"
        )
        assert captured["provider_id"] == (
            "provider-a"
        )
        assert captured["provider_ref"] == (
            "provider-a.action"
        )
        assert captured["action"] == "refund"
        assert captured["window_hours"] == 168
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_learning_trend_route_validates_window():
    user_id = uuid4()

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/capabilities/"
                "learning-observations/trends",
                params={
                    "window_hours": 5000,
                },
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
