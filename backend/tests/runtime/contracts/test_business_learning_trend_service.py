from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.learning import (
    BusinessLearningAggregationPolicy,
    BusinessLearningTrendDirection,
    BusinessLearningTrendService,
)


NOW = datetime(
    2026,
    8,
    2,
    12,
    0,
    tzinfo=timezone.utc,
)


class FakeBusinessLearningRepository:
    def __init__(
        self,
        rows,
    ):
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
            "objective_namespace",
            "objective_type",
            "decision",
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
    result,
    tenant_id="tenant-a",
    objective_namespace=(
        "customer_service.support"
    ),
    objective_type="multi_operation",
    decision="approved",
):
    return SimpleNamespace(
        user_id=user_id,
        observed_at=observed_at,
        tenant_id=tenant_id,
        objective_namespace=objective_namespace,
        objective_type=objective_type,
        decision=decision,
        result=result,
        confidence=1.0,
        is_final=True,
        retryable=False,
        operation_count=1,
        achieved_operation_count=(
            1 if result == "achieved" else 0
        ),
        failed_operation_count=(
            1 if result == "failed" else 0
        ),
        pending_operation_count=0,
        unknown_operation_count=0,
        not_executed_operation_count=0,
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
                result=(
                    "achieved"
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
                result=(
                    "achieved"
                    if index < 9
                    else "failed"
                ),
            )
            for index in range(10)
        ],
    ]

    repository = (
        FakeBusinessLearningRepository(
            rows
        )
    )

    service = BusinessLearningTrendService(
        db=SimpleNamespace(),
        repository=repository,
        aggregation_policy=(
            BusinessLearningAggregationPolicy(
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
    assert report.failure_rate_delta == (
        pytest.approx(-0.4)
    )
    assert report.trend_direction == (
        BusinessLearningTrendDirection
        .IMPROVING
    )

    assert (
        repository.calls[0]["window_hours"]
        == 336
    )
    assert (
        repository.calls[0]["user_id"]
        == user_id
    )


@pytest.mark.asyncio
async def test_trend_service_preserves_scope():
    user_id = uuid4()

    rows = [
        observation(
            user_id=user_id,
            observed_at=(
                NOW - timedelta(days=10)
            ),
            result="achieved",
            decision="approved",
        ),
        observation(
            user_id=user_id,
            observed_at=(
                NOW - timedelta(days=3)
            ),
            result="achieved",
            decision="approved",
        ),
        observation(
            user_id=user_id,
            observed_at=(
                NOW - timedelta(days=10)
            ),
            result=(
                "intentionally_not_executed"
            ),
            decision="rejected",
        ),
        observation(
            user_id=user_id,
            observed_at=(
                NOW - timedelta(days=3)
            ),
            result=(
                "intentionally_not_executed"
            ),
            decision="rejected",
        ),
    ]

    service = BusinessLearningTrendService(
        db=SimpleNamespace(),
        repository=(
            FakeBusinessLearningRepository(
                rows
            )
        ),
        aggregation_policy=(
            BusinessLearningAggregationPolicy(
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
        report.decision
        for report in reports
    } == {
        "approved",
        "rejected",
    }


@pytest.mark.asyncio
async def test_missing_historical_window_is_insufficient():
    user_id = uuid4()

    rows = [
        observation(
            user_id=user_id,
            observed_at=(
                NOW - timedelta(days=3)
            ),
            result="achieved",
        )
        for _ in range(5)
    ]

    service = BusinessLearningTrendService(
        db=SimpleNamespace(),
        repository=(
            FakeBusinessLearningRepository(
                rows
            )
        ),
        aggregation_policy=(
            BusinessLearningAggregationPolicy(
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
        BusinessLearningTrendDirection
        .INSUFFICIENT_EVIDENCE
    )


@pytest.mark.asyncio
async def test_trend_service_applies_filters():
    user_id = uuid4()
    repository = (
        FakeBusinessLearningRepository([])
    )

    service = BusinessLearningTrendService(
        db=SimpleNamespace(),
        repository=repository,
    )

    reports = await service.analyze(
        user_id=user_id,
        window_hours=24,
        tenant_id="tenant-a",
        objective_namespace=(
            "customer_service.support"
        ),
        objective_type="refund",
        decision="approved",
        now=NOW,
    )

    assert reports == []

    call = repository.calls[0]

    assert call["user_id"] == user_id
    assert call["tenant_id"] == "tenant-a"
    assert (
        call["objective_namespace"]
        == "customer_service.support"
    )
    assert call["objective_type"] == "refund"
    assert call["decision"] == "approved"


@pytest.mark.asyncio
async def test_trend_service_rejects_excessive_window():
    service = BusinessLearningTrendService(
        db=SimpleNamespace(),
        repository=(
            FakeBusinessLearningRepository([])
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
