from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.runtime.capabilities.execution.learning import (
    CapabilityLearningInterpretation,
    CapabilityLearningQualityLevel,
    CapabilityLearningSummary,
    CapabilityLearningSummaryService,
)


class FakeUser:
    def __init__(
        self,
        user_id,
    ):
        self.id = user_id


@pytest.mark.asyncio
async def test_learning_summary_route_is_authenticated_and_scoped(
    monkeypatch,
):
    user_id = uuid4()
    captured = {}

    async def fake_summarize(
        self,
        **kwargs,
    ):
        captured.update(kwargs)
        now = datetime.now(timezone.utc)

        return [
            CapabilityLearningSummary(
                capability_id="capability.a",
                provider_id="provider-a",
                provider_ref="provider-a.action",
                tenant_id="tenant-a",
                action="refund",
                window_start=now,
                window_end=now,
                total_observations=3,
                final_observations=3,
                retryable_observations=0,
                observations_with_evidence=3,
                verified=3,
                partially_verified=0,
                failed=0,
                inconclusive=0,
                not_verifiable=0,
                average_confidence=1.0,
                evidence_coverage=1.0,
                finality_ratio=1.0,
                effective_sample_size=3.0,
                weighted_positive_mass=3.0,
                weighted_negative_mass=0.0,
                weighted_unresolved_mass=0.0,
                estimated_success_rate=1.0,
                summary_confidence=1.0,
                minimum_effective_sample_size=2.0,
                evidence_sufficient=True,
                dominant_outcome="verified",
                quality_level=(
                    CapabilityLearningQualityLevel
                    .HIGH
                ),
                interpretation=(
                    CapabilityLearningInterpretation
                    .POSITIVE
                ),
            )
        ]

    monkeypatch.setattr(
        CapabilityLearningSummaryService,
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
                "/capabilities/"
                "learning-observations/summary",
                params={
                    "tenant_id": "tenant-a",
                    "capability_id": "capability.a",
                    "provider_id": "provider-a",
                    "action": "refund",
                    "window_hours": 168,
                    "minimum_effective_sample_size": 2,
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1
        assert (
            body[0]["capability_id"]
            == "capability.a"
        )
        assert (
            body[0]["quality_level"]
            == "high"
        )
        assert (
            body[0]["interpretation"]
            == "positive"
        )

        assert captured["user_id"] == user_id
        assert captured["tenant_id"] == "tenant-a"
        assert captured["provider_id"] == "provider-a"
        assert captured["action"] == "refund"
        assert captured["window_hours"] == 168
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_learning_summary_route_validates_window():
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
                "learning-observations/summary",
                params={
                    "window_hours": 0,
                },
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
