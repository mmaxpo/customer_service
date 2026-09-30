from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.capabilities.execution.learning import (
    CapabilityLearningAggregationPolicy,
    CapabilityLearningTrendDirection,
    CapabilityLearningTrendService,
)


NOW = datetime(
    2026,
    7,
    19,
    12,
    0,
    tzinfo=timezone.utc,
)


class FakeLearningRepository:
    def __init__(self, rows):
        self.rows = list(rows)
        self.calls = []

    async def list_for_aggregation(
        self,
        **kwargs,
    ):
        self.calls.append(kwargs)

        end = kwargs["now"]
        start = end - timedelta(
            hours=kwargs["window_hours"]
        )

        rows = [
            row
            for row in self.rows
            if (
                row.user_id
                == kwargs["user_id"]
                and start
                <= row.observed_at
                < end
            )
        ]

        for key in (
            "tenant_id",
            "capability_id",
            "provider_id",
            "provider_ref",
            "action",
        ):
            value = kwargs.get(key)

            if value is not None:
                rows = [
                    row
                    for row in rows
                    if getattr(row, key) == value
                ]

        return start, end, rows


def observation(
    *,
    user_id,
    observed_at,
    outcome,
    capability_id="capability.a",
    provider_id="provider-a",
    provider_ref="provider-a.action",
    tenant_id="tenant-a",
    action="execute",
):
    return SimpleNamespace(
        user_id=user_id,
        observed_at=observed_at,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
        tenant_id=tenant_id,
        action=action,
        outcome=outcome,
        confidence=1.0,
        is_final=True,
        retryable=False,
        evidence_summary_json={
            "count": 1,
            "items": [],
        },
    )


@pytest.mark.asyncio
async def test_trend_service_compares_adjacent_windows():
    user_id = uuid4()

    rows = [
        *[
            observation(
                user_id=user_id,
                observed_at=(
                    NOW
                    - timedelta(days=10)
                    + timedelta(minutes=index)
                ),
                outcome=(
                    "verified"
                    if index < 5
                    else "failed"
                ),
            )
            for index in range(10)
        ],
        *[
            observation(
                user_id=user_id,
                observed_at=(
                    NOW
                    - timedelta(days=3)
                    + timedelta(minutes=index)
                ),
                outcome=(
                    "verified"
                    if index < 9
                    else "failed"
                ),
            )
            for index in range(10)
        ],
    ]

    repository = FakeLearningRepository(
        rows
    )

    service = CapabilityLearningTrendService(
        db=SimpleNamespace(),
        repository=repository,
        aggregation_policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=5
            )
        ),
    )

    reports = await service.analyze(
        user_id=user_id,
        window_hours=168,
        now=NOW,
    )

    assert len(reports) == 1

    report = reports[0]

    assert (
        report.historical.window_end
        == report.recent.window_start
    )
    assert (
        report.historical.total_observations
        == 10
    )
    assert (
        report.recent.total_observations
        == 10
    )
    assert report.success_rate_delta == (
        pytest.approx(0.4)
    )
    assert report.trend_direction == (
        CapabilityLearningTrendDirection
        .IMPROVING
    )

    assert (
        repository.calls[0]["window_hours"]
        == 336
    )
    assert repository.calls[0]["user_id"] == (
        user_id
    )


@pytest.mark.asyncio
async def test_trend_service_preserves_full_scope():
    user_id = uuid4()

    rows = [
        observation(
            user_id=user_id,
            observed_at=(
                NOW - timedelta(days=10)
            ),
            outcome="verified",
            action="refund",
        ),
        observation(
            user_id=user_id,
            observed_at=(
                NOW - timedelta(days=3)
            ),
            outcome="verified",
            action="refund",
        ),
        observation(
            user_id=user_id,
            observed_at=(
                NOW - timedelta(days=10)
            ),
            outcome="failed",
            action="cancel",
        ),
        observation(
            user_id=user_id,
            observed_at=(
                NOW - timedelta(days=3)
            ),
            outcome="failed",
            action="cancel",
        ),
    ]

    service = CapabilityLearningTrendService(
        db=SimpleNamespace(),
        repository=FakeLearningRepository(
            rows
        ),
        aggregation_policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=1
            )
        ),
    )

    reports = await service.analyze(
        user_id=user_id,
        window_hours=168,
        now=NOW,
    )

    assert len(reports) == 2
    assert {
        report.action
        for report in reports
    } == {"refund", "cancel"}


@pytest.mark.asyncio
async def test_missing_historical_window_is_insufficient():
    user_id = uuid4()

    rows = [
        observation(
            user_id=user_id,
            observed_at=(
                NOW - timedelta(days=3)
            ),
            outcome="verified",
        )
        for _ in range(5)
    ]

    service = CapabilityLearningTrendService(
        db=SimpleNamespace(),
        repository=FakeLearningRepository(
            rows
        ),
        aggregation_policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=2
            )
        ),
    )

    reports = await service.analyze(
        user_id=user_id,
        window_hours=168,
        now=NOW,
    )

    assert len(reports) == 1

    report = reports[0]

    assert (
        report.historical.total_observations
        == 0
    )
    assert (
        report.recent.total_observations
        == 5
    )
    assert (
        report.comparison_evidence_sufficient
        is False
    )
    assert report.trend_direction == (
        CapabilityLearningTrendDirection
        .INSUFFICIENT_EVIDENCE
    )


@pytest.mark.asyncio
async def test_trend_service_applies_authenticated_filters():
    user_id = uuid4()

    repository = FakeLearningRepository(
        []
    )

    service = CapabilityLearningTrendService(
        db=SimpleNamespace(),
        repository=repository,
    )

    reports = await service.analyze(
        user_id=user_id,
        window_hours=24,
        tenant_id="tenant-a",
        capability_id="capability.a",
        provider_id="provider-a",
        provider_ref="provider-a.action",
        action="refund",
        now=NOW,
    )

    assert reports == []

    call = repository.calls[0]

    assert call["user_id"] == user_id
    assert call["tenant_id"] == "tenant-a"
    assert call["capability_id"] == (
        "capability.a"
    )
    assert call["provider_id"] == (
        "provider-a"
    )
    assert call["provider_ref"] == (
        "provider-a.action"
    )
    assert call["action"] == "refund"


@pytest.mark.asyncio
async def test_trend_service_rejects_excessive_window():
    service = CapabilityLearningTrendService(
        db=SimpleNamespace(),
        repository=FakeLearningRepository(
            []
        ),
    )

    with pytest.raises(
        ValueError,
        match="between 1 and 4380",
    ):
        await service.analyze(
            user_id=uuid4(),
            window_hours=4381,
        )
