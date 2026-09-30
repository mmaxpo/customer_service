from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.runtime.learning import (
    BusinessLearningAdvisoryStatus,
    BusinessLearningApprovalStatus,
    BusinessLearningCandidateGenerationItem,
    BusinessLearningCandidateGenerationResult,
    BusinessLearningCandidateStatus,
    BusinessLearningEvidenceLevel,
    BusinessLearningInsightCandidate,
    BusinessLearningInsightCandidateFactory,
    BusinessLearningInsightCandidateOperations,
    BusinessLearningInterpretation,
    BusinessLearningStabilityLevel,
    BusinessLearningSummary,
    BusinessLearningTrendDirection,
    BusinessLearningTrendReport,
)


BASE = (
    "/customer-service/analytics/"
    "business-learning/insight-candidates"
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


def summary(
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


def report() -> BusinessLearningTrendReport:
    historical = summary(recent=False)
    recent = summary(recent=True)

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
        explanation="Stable evidence.",
    )


def candidate() -> BusinessLearningInsightCandidate:
    return (
        BusinessLearningInsightCandidateFactory()
        .propose(
            report=report(),
            proposed_at=NOW,
        )
    )


@pytest.mark.asyncio
async def test_generate_route_is_authenticated_and_scoped(
    monkeypatch,
):
    user_id = uuid4()
    generated = candidate()
    captured = {}

    async def fake_generate(
        self,
        *,
        user_id,
        request,
    ):
        captured["user_id"] = user_id
        captured["request"] = request

        return (
            BusinessLearningCandidateGenerationResult(
                analyzed_reports=1,
                eligible_interpretations=1,
                created_candidates=1,
                existing_candidates=0,
                items=(
                    BusinessLearningCandidateGenerationItem(
                        candidate=generated,
                        created=True,
                    ),
                ),
            )
        )

    monkeypatch.setattr(
        BusinessLearningInsightCandidateOperations,
        "generate",
        fake_generate,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                f"{BASE}/generate",
                json={
                    "tenant_id": "tenant-a",
                    "objective_namespace": (
                        "customer_service.support"
                    ),
                    "objective_type": (
                        "multi_operation"
                    ),
                    "decision": "approved",
                    "window_hours": 24,
                },
            )

        assert response.status_code == 201
        assert (
            response.json()["created_candidates"]
            == 1
        )
        assert captured["user_id"] == user_id
        assert (
            captured["request"].tenant_id
            == "tenant-a"
        )
        assert (
            captured["request"]
            .objective_namespace
            == "customer_service.support"
        )
        assert (
            captured["request"].window_hours
            == 24
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_list_route_forwards_filters(
    monkeypatch,
):
    user_id = uuid4()
    item = candidate()
    captured = {}

    async def fake_list_latest(
        self,
        **kwargs,
    ):
        captured.update(kwargs)
        return [item]

    monkeypatch.setattr(
        BusinessLearningInsightCandidateOperations,
        "list_latest",
        fake_list_latest,
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
                    "status": "validated",
                    "approval_status": "pending",
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
        assert captured["status"] == "validated"
        assert (
            captured["approval_status"]
            == "pending"
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_get_history_and_review_routes(
    monkeypatch,
):
    user_id = uuid4()
    original = candidate()
    approved = (
        BusinessLearningInsightCandidateFactory()
        .review(
            candidate=original,
            approved=True,
            reviewed_by_user_id=user_id,
            reason="Confirmed.",
            reviewed_at=NOW,
        )
    )

    async def fake_get_latest(
        self,
        *,
        user_id,
        candidate_id,
    ):
        return original

    async def fake_history(
        self,
        *,
        user_id,
        candidate_id,
    ):
        return [original, approved]

    async def fake_review(
        self,
        *,
        user_id,
        candidate_id,
        reviewed_by_user_id,
        request,
    ):
        assert reviewed_by_user_id == user_id
        assert request.reason == "Confirmed."
        return approved

    monkeypatch.setattr(
        BusinessLearningInsightCandidateOperations,
        "get_latest",
        fake_get_latest,
    )
    monkeypatch.setattr(
        BusinessLearningInsightCandidateOperations,
        "history",
        fake_history,
    )
    monkeypatch.setattr(
        BusinessLearningInsightCandidateOperations,
        "review",
        fake_review,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    candidate_id = original.candidate_id

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            get_response = await client.get(
                f"{BASE}/{candidate_id}"
            )
            history_response = await client.get(
                f"{BASE}/{candidate_id}/history"
            )
            review_response = await client.post(
                f"{BASE}/{candidate_id}/review",
                json={
                    "decision": "approve",
                    "reason": "Confirmed.",
                },
            )

        assert get_response.status_code == 200
        assert history_response.status_code == 200
        assert len(history_response.json()) == 2

        assert review_response.status_code == 200
        assert (
            review_response.json()["status"]
            == "approved"
        )
        assert (
            review_response.json()[
                "approval_status"
            ]
            == "approved"
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "suffix",
    [
        f"/{uuid4()}",
        f"/{uuid4()}/history",
        f"/{uuid4()}/review",
    ],
)
async def test_missing_candidate_returns_404(
    monkeypatch,
    suffix,
):
    async def fake_get_latest(
        self,
        **kwargs,
    ):
        return None

    async def fake_history(
        self,
        **kwargs,
    ):
        return []

    async def fake_review(
        self,
        **kwargs,
    ):
        return None

    monkeypatch.setattr(
        BusinessLearningInsightCandidateOperations,
        "get_latest",
        fake_get_latest,
    )
    monkeypatch.setattr(
        BusinessLearningInsightCandidateOperations,
        "history",
        fake_history,
    )
    monkeypatch.setattr(
        BusinessLearningInsightCandidateOperations,
        "review",
        fake_review,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(uuid4())

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            if suffix.endswith("/review"):
                response = await client.post(
                    f"{BASE}{suffix}",
                    json={
                        "decision": "reject",
                        "reason": "Not accepted.",
                    },
                )
            else:
                response = await client.get(
                    f"{BASE}{suffix}"
                )

        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_review_value_error_returns_422(
    monkeypatch,
):
    async def fake_review(
        self,
        **kwargs,
    ):
        raise ValueError(
            "Only a pending validated business "
            "candidate can be reviewed"
        )

    monkeypatch.setattr(
        BusinessLearningInsightCandidateOperations,
        "review",
        fake_review,
    )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(uuid4())

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                f"{BASE}/{uuid4()}/review",
                json={
                    "decision": "approve",
                    "reason": "Repeated.",
                },
            )

        assert response.status_code == 422
        assert "pending validated" in (
            response.json()["detail"]
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        (
            "POST",
            f"{BASE}/generate",
            {},
        ),
        (
            "GET",
            BASE,
            None,
        ),
        (
            "GET",
            f"{BASE}/{uuid4()}",
            None,
        ),
        (
            "GET",
            f"{BASE}/{uuid4()}/history",
            None,
        ),
        (
            "POST",
            f"{BASE}/{uuid4()}/review",
            {
                "decision": "approve",
                "reason": "Confirmed.",
            },
        ),
    ],
)
async def test_candidate_routes_require_authentication(
    method,
    path,
    payload,
):
    app.dependency_overrides.pop(
        get_current_user,
        None,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.request(
            method,
            path,
            json=payload,
        )

    assert response.status_code in {
        401,
        403,
    }


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
        (
            BASE,
            {"status": "promoted"},
        ),
        (
            BASE,
            {
                "approval_status": "unknown"
            },
        ),
    ],
)
async def test_candidate_list_validates_query(
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
