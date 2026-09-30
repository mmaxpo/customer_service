from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.runtime.learning import (
    BusinessLearningAdvisoryStatus,
    BusinessLearningEvidenceLevel,
    BusinessLearningInterpretation,
    BusinessLearningStabilityLevel,
    BusinessLearningSummary,
    BusinessLearningTrendDirection,
    BusinessLearningTrendReport,
    BusinessLearningTrendService,
)


ROUTE = (
    "/customer-service/analytics/"
    "business-learning/trends"
)


class FakeUser:
    def __init__(
        self,
        user_id,
    ) -> None:
        self.id = user_id


def summary(
    *,
    start,
    end,
) -> BusinessLearningSummary:
    return BusinessLearningSummary(
        tenant_id="tenant-a",
        objective_namespace=(
            "customer_service.support"
        ),
        objective_type="multi_operation",
        decision="approved",
        window_start=start,
        window_end=end,
        total_observations=5,
        final_observations=5,
        retryable_observations=0,
        observations_with_evidence=5,
        achieved=5,
        partially_achieved=0,
        progressing=0,
        failed=0,
        intentionally_not_executed=0,
        inconclusive=0,
        total_operations=5,
        achieved_operations=5,
        failed_operations=0,
        pending_operations=0,
        unknown_operations=0,
        not_executed_operations=0,
        average_confidence=1.0,
        evidence_coverage=1.0,
        finality_ratio=1.0,
        effective_sample_size=5.0,
        weighted_success_mass=5.0,
        weighted_failure_mass=0.0,
        weighted_unresolved_mass=0.0,
        weighted_not_executed_mass=0.0,
        estimated_success_rate=1.0,
        estimated_failure_rate=0.0,
        summary_confidence=1.0,
        minimum_effective_sample_size=5.0,
        evidence_sufficient=True,
        dominant_result="achieved",
        evidence_level=(
            BusinessLearningEvidenceLevel.HIGH
        ),
        interpretation=(
            BusinessLearningInterpretation.POSITIVE
        ),
    )


@pytest.mark.asyncio
async def test_business_learning_trend_route_is_authenticated_and_scoped(
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
            BusinessLearningTrendReport(
                tenant_id="tenant-a",
                objective_namespace=(
                    "customer_service.support"
                ),
                objective_type=(
                    "multi_operation"
                ),
                decision="approved",
                historical=historical,
                recent=recent,
                historical_evidence_sufficient=True,
                recent_evidence_sufficient=True,
                comparison_evidence_sufficient=True,
                success_rate_delta=0.0,
                failure_rate_delta=0.0,
                confidence_delta=0.0,
                effective_sample_delta=0.0,
                result_distribution_divergence=0.0,
                contradiction_score=0.0,
                stability_score=1.0,
                interpretation_changed=False,
                dominant_result_changed=False,
                direct_interpretation_conflict=False,
                trend_direction=(
                    BusinessLearningTrendDirection.STABLE
                ),
                stability_level=(
                    BusinessLearningStabilityLevel.STABLE
                ),
                advisory_status=(
                    BusinessLearningAdvisoryStatus.TRUST
                ),
                explanation=(
                    "Stable business learning evidence."
                ),
            )
        ]

    monkeypatch.setattr(
        BusinessLearningTrendService,
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
                ROUTE,
                params={
                    "window_hours": 168,
                    "tenant_id": "tenant-a",
                    "objective_namespace": (
                        "customer_service.support"
                    ),
                    "objective_type": (
                        "multi_operation"
                    ),
                    "decision": "approved",
                    "minimum_effective_sample_size": 4,
                    "meaningful_success_delta": 0.15,
                    "meaningful_failure_delta": 0.15,
                    "contradiction_threshold": 0.70,
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
        assert captured["window_hours"] == 168
        assert (
            captured["tenant_id"]
            == "tenant-a"
        )
        assert (
            captured["objective_namespace"]
            == "customer_service.support"
        )
        assert (
            captured["objective_type"]
            == "multi_operation"
        )
        assert (
            captured["decision"]
            == "approved"
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("window_hours", 0),
        ("window_hours", 4381),
        (
            "minimum_effective_sample_size",
            0.0,
        ),
        ("meaningful_success_delta", -0.1),
        ("meaningful_failure_delta", 1.1),
        ("contradiction_threshold", 1.1),
    ],
)
async def test_business_learning_trend_route_validates_query(
    parameter,
    value,
):
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
                ROUTE,
                params={
                    parameter: value,
                },
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_business_learning_trend_route_requires_authentication():
    app.dependency_overrides.pop(
        get_current_user,
        None,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            ROUTE
        )

    assert response.status_code in {
        401,
        403,
    }
