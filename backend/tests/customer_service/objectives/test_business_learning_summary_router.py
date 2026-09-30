from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.runtime.learning import (
    BusinessLearningEvidenceLevel,
    BusinessLearningInterpretation,
    BusinessLearningSummary,
    BusinessLearningSummaryService,
)


ROUTE = (
    "/customer-service/analytics/"
    "business-learning/summary"
)


class FakeUser:
    def __init__(
        self,
        user_id,
    ) -> None:
        self.id = user_id


@pytest.mark.asyncio
async def test_business_learning_summary_route_is_authenticated_and_scoped(
    monkeypatch,
):
    user_id = uuid4()
    captured = {}

    async def fake_summarize(
        self,
        **kwargs,
    ):
        captured.update(kwargs)
        now = datetime.now(
            timezone.utc
        )

        return [
            BusinessLearningSummary(
                tenant_id="tenant-a",
                objective_namespace=(
                    "customer_service.support"
                ),
                objective_type=(
                    "multi_operation"
                ),
                decision="approved",
                window_start=now,
                window_end=now,
                total_observations=3,
                final_observations=3,
                retryable_observations=0,
                observations_with_evidence=3,
                achieved=2,
                partially_achieved=1,
                progressing=0,
                failed=0,
                intentionally_not_executed=0,
                inconclusive=0,
                total_operations=4,
                achieved_operations=3,
                failed_operations=0,
                pending_operations=1,
                unknown_operations=0,
                not_executed_operations=0,
                average_confidence=0.9,
                evidence_coverage=1.0,
                finality_ratio=1.0,
                effective_sample_size=2.7,
                weighted_success_mass=2.25,
                weighted_failure_mass=0.0,
                weighted_unresolved_mass=0.45,
                weighted_not_executed_mass=0.0,
                estimated_success_rate=(
                    2.25 / 2.7
                ),
                estimated_failure_rate=0.0,
                summary_confidence=0.9,
                minimum_effective_sample_size=2.0,
                evidence_sufficient=True,
                dominant_result="achieved",
                evidence_level=(
                    BusinessLearningEvidenceLevel
                    .HIGH
                ),
                interpretation=(
                    BusinessLearningInterpretation
                    .POSITIVE
                ),
            )
        ]

    monkeypatch.setattr(
        BusinessLearningSummaryService,
        "summarize",
        fake_summarize,
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
                    "minimum_effective_sample_size": (
                        2.0
                    ),
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1
        assert (
            body[0]["objective_namespace"]
            == "customer_service.support"
        )
        assert (
            body[0]["objective_type"]
            == "multi_operation"
        )
        assert (
            body[0]["decision"]
            == "approved"
        )
        assert (
            body[0]["evidence_level"]
            == "high"
        )
        assert (
            body[0]["interpretation"]
            == "positive"
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
        ("window_hours", 8761),
        (
            "minimum_effective_sample_size",
            0.0,
        ),
    ],
)
async def test_business_learning_summary_route_validates_query(
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
async def test_business_learning_summary_route_requires_authentication():
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
