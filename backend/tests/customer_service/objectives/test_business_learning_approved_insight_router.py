from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.runtime.learning import (
    BusinessLearningAdvisoryStatus,
    BusinessLearningApprovedInsightProjection,
    BusinessLearningApprovedInsightService,
    BusinessLearningEvidenceLevel,
    BusinessLearningInsightCandidateFactory,
    BusinessLearningInterpretation,
    BusinessLearningStabilityLevel,
    BusinessLearningSummary,
    BusinessLearningTrendDirection,
    BusinessLearningTrendReport,
)


BASE = (
    "/customer-service/analytics/"
    "business-learning/approved-insights"
)

NOW = datetime(
    2026,
    8,
    2,
    12,
    0,
    tzinfo=timezone.utc,
)


class FakeUser:
    def __init__(
        self,
        user_id,
    ) -> None:
        self.id = user_id


def _summary(
    *,
    recent: bool,
) -> BusinessLearningSummary:
    start = (
        NOW - timedelta(days=7)
        if recent
        else NOW - timedelta(days=14)
    )
    end = (
        NOW
        if recent
        else NOW - timedelta(days=7)
    )

    return BusinessLearningSummary(
        tenant_id="tenant-a",
        objective_namespace=(
            "customer_service.support"
        ),
        objective_type="multi_operation",
        decision="approved",
        window_start=start,
        window_end=end,
        total_observations=10,
        final_observations=10,
        retryable_observations=0,
        observations_with_evidence=10,
        achieved=9,
        partially_achieved=0,
        progressing=0,
        failed=1,
        intentionally_not_executed=0,
        inconclusive=0,
        total_operations=10,
        achieved_operations=9,
        failed_operations=1,
        pending_operations=0,
        unknown_operations=0,
        not_executed_operations=0,
        average_confidence=0.95,
        evidence_coverage=1.0,
        finality_ratio=1.0,
        effective_sample_size=10.0,
        weighted_success_mass=9.0,
        weighted_failure_mass=1.0,
        weighted_unresolved_mass=0.0,
        weighted_not_executed_mass=0.0,
        estimated_success_rate=0.9,
        estimated_failure_rate=0.1,
        summary_confidence=0.95,
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


def _report() -> BusinessLearningTrendReport:
    historical = _summary(recent=False)
    recent = _summary(recent=True)

    return BusinessLearningTrendReport(
        tenant_id=historical.tenant_id,
        objective_namespace=(
            historical.objective_namespace
        ),
        objective_type=historical.objective_type,
        decision=historical.decision,
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
        contradiction_score=0.05,
        stability_score=0.95,
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
        explanation="Stable business evidence.",
    )


def _approved_insight():
    factory = (
        BusinessLearningInsightCandidateFactory()
    )

    candidate = factory.propose(
        report=_report(),
        proposed_at=NOW,
    )

    approved = factory.review(
        candidate=candidate,
        approved=True,
        reviewed_by_user_id=uuid4(),
        reason="Evidence accepted.",
        reviewed_at=NOW,
    )

    return (
        BusinessLearningApprovedInsightProjection
        .from_candidate(approved)
    )


@pytest.mark.asyncio
async def test_list_route_forwards_authenticated_scope(
    monkeypatch,
):
    user_id = uuid4()
    insight = _approved_insight()
    captured = {}

    async def fake_list_approved(
        self,
        **kwargs,
    ):
        captured.update(kwargs)
        return [insight]

    monkeypatch.setattr(
        BusinessLearningApprovedInsightService,
        "list_approved",
        fake_list_approved,
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
                BASE,
                params={
                    "tenant_id": "tenant-a",
                    "objective_namespace": (
                        "customer_service.support"
                    ),
                    "objective_type": (
                        "multi_operation"
                    ),
                    "decision": "approved",
                    "limit": 25,
                    "offset": 5,
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["limit"] == 25
        assert body["offset"] == 5
        assert len(body["items"]) == 1

        assert captured["user_id"] == user_id
        assert captured["tenant_id"] == (
            "tenant-a"
        )
        assert (
            captured["objective_namespace"]
            == "customer_service.support"
        )
        assert (
            captured["objective_type"]
            == "multi_operation"
        )
        assert captured["decision"] == "approved"
        assert captured["limit"] == 25
        assert captured["offset"] == 5
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_get_route_returns_approved_insight(
    monkeypatch,
):
    user_id = uuid4()
    insight = _approved_insight()
    captured = {}

    async def fake_get_approved(
        self,
        *,
        user_id,
        candidate_id,
    ):
        captured["user_id"] = user_id
        captured["candidate_id"] = (
            candidate_id
        )
        return insight

    monkeypatch.setattr(
        BusinessLearningApprovedInsightService,
        "get_approved",
        fake_get_approved,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    candidate_id = (
        insight.provenance.candidate_id
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"{BASE}/{candidate_id}"
            )

        assert response.status_code == 200

        body = response.json()

        assert body["provenance"][
            "candidate_id"
        ] == str(candidate_id)

        assert body["read_only"] is True
        assert (
            body["operator_review_only"]
            is True
        )
        assert (
            body["affects_planning"]
            is False
        )
        assert (
            body["affects_workflows"]
            is False
        )
        assert (
            body["affects_routing"]
            is False
        )
        assert (
            body["affects_runtime_policy"]
            is False
        )
        assert (
            body["authorizes_business_action"]
            is False
        )

        assert captured["user_id"] == user_id
        assert (
            captured["candidate_id"]
            == candidate_id
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_get_route_hides_missing_or_nonapproved(
    monkeypatch,
):
    async def fake_get_approved(
        self,
        **kwargs,
    ):
        return None

    monkeypatch.setattr(
        BusinessLearningApprovedInsightService,
        "get_approved",
        fake_get_approved,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(uuid4())

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"{BASE}/{uuid4()}"
            )

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "Approved business-learning insight "
            "not found"
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "params"),
    [
        (
            BASE,
            {"limit": 0},
        ),
        (
            BASE,
            {"limit": 501},
        ),
        (
            BASE,
            {"offset": -1},
        ),
    ],
)
async def test_list_route_validates_pagination(
    path,
    params,
):
    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(uuid4())

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                path,
                params=params,
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        BASE,
        f"{BASE}/{uuid4()}",
    ],
)
async def test_approved_insight_routes_require_authentication(
    path,
):
    app.dependency_overrides.pop(
        get_current_user,
        None,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(path)

    assert response.status_code in {
        401,
        403,
    }


@pytest.mark.asyncio
async def test_route_payload_has_no_activation_fields(
    monkeypatch,
):
    insight = _approved_insight()

    async def fake_get_approved(
        self,
        **kwargs,
    ):
        return insight

    monkeypatch.setattr(
        BusinessLearningApprovedInsightService,
        "get_approved",
        fake_get_approved,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(uuid4())

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"{BASE}/"
                f"{insight.provenance.candidate_id}"
            )

        assert response.status_code == 200

        body = response.json()

        assert "promotion_id" not in body
        assert "promotion_target" not in body
        assert "active" not in body
        assert "revoked" not in body
        assert "recommended_behavior" not in body
        assert "recommended_review" in body
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
