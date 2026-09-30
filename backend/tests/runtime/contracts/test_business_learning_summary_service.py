from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.learning import (
    BusinessLearningAggregationPolicy,
    BusinessLearningInterpretation,
    BusinessLearningSummaryService,
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

        window_end = (
            kwargs.get("now")
            or datetime.now(timezone.utc)
        )
        window_start = (
            window_end
            - timedelta(
                hours=kwargs["window_hours"]
            )
        )

        rows = [
            row
            for row in self.rows
            if row.user_id == kwargs["user_id"]
        ]

        for name in (
            "tenant_id",
            "objective_namespace",
            "objective_type",
            "decision",
        ):
            value = kwargs.get(name)

            if value is not None:
                rows = [
                    row
                    for row in rows
                    if getattr(row, name) == value
                ]

        return (
            window_start,
            window_end,
            rows,
        )


def observation(
    *,
    user_id,
    tenant_id,
    objective_namespace,
    objective_type,
    decision,
    result,
):
    return SimpleNamespace(
        user_id=user_id,
        tenant_id=tenant_id,
        objective_namespace=(
            objective_namespace
        ),
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
async def test_summary_service_groups_by_full_scope():
    user_id = uuid4()

    repository = (
        FakeBusinessLearningRepository(
            [
                observation(
                    user_id=user_id,
                    tenant_id="tenant-a",
                    objective_namespace=(
                        "customer_service.support"
                    ),
                    objective_type=(
                        "multi_operation"
                    ),
                    decision="approved",
                    result="achieved",
                ),
                observation(
                    user_id=user_id,
                    tenant_id="tenant-a",
                    objective_namespace=(
                        "customer_service.support"
                    ),
                    objective_type=(
                        "multi_operation"
                    ),
                    decision="approved",
                    result="failed",
                ),
                observation(
                    user_id=user_id,
                    tenant_id="tenant-a",
                    objective_namespace=(
                        "customer_service.support"
                    ),
                    objective_type=(
                        "multi_operation"
                    ),
                    decision="rejected",
                    result=(
                        "intentionally_not_executed"
                    ),
                ),
            ]
        )
    )

    service = BusinessLearningSummaryService(
        db=SimpleNamespace(),
        repository=repository,
        policy=(
            BusinessLearningAggregationPolicy(
                minimum_effective_sample_size=1.0
            )
        ),
    )

    summaries = await service.summarize(
        user_id=user_id,
        window_hours=24,
    )

    assert len(summaries) == 2

    approved = next(
        summary
        for summary in summaries
        if summary.decision == "approved"
    )
    rejected = next(
        summary
        for summary in summaries
        if summary.decision == "rejected"
    )

    assert approved.total_observations == 2
    assert approved.achieved == 1
    assert approved.failed == 1
    assert approved.estimated_success_rate == 0.5
    assert approved.estimated_failure_rate == 0.5

    assert rejected.total_observations == 1
    assert (
        rejected.intentionally_not_executed
        == 1
    )
    assert rejected.interpretation == (
        BusinessLearningInterpretation
        .NOT_EXECUTED
    )


@pytest.mark.asyncio
async def test_summary_service_preserves_user_scope():
    current_user_id = uuid4()
    other_user_id = uuid4()

    repository = (
        FakeBusinessLearningRepository(
            [
                observation(
                    user_id=current_user_id,
                    tenant_id=None,
                    objective_namespace=(
                        "customer_service.support"
                    ),
                    objective_type="single_operation",
                    decision="approved",
                    result="achieved",
                ),
                observation(
                    user_id=other_user_id,
                    tenant_id=None,
                    objective_namespace=(
                        "customer_service.support"
                    ),
                    objective_type="single_operation",
                    decision="approved",
                    result="failed",
                ),
            ]
        )
    )

    service = BusinessLearningSummaryService(
        db=SimpleNamespace(),
        repository=repository,
        policy=(
            BusinessLearningAggregationPolicy(
                minimum_effective_sample_size=1.0
            )
        ),
    )

    summaries = await service.summarize(
        user_id=current_user_id,
    )

    assert len(summaries) == 1
    assert summaries[0].achieved == 1
    assert summaries[0].failed == 0
    assert (
        repository.calls[0]["user_id"]
        == current_user_id
    )


@pytest.mark.asyncio
async def test_summary_service_applies_filters():
    user_id = uuid4()

    repository = (
        FakeBusinessLearningRepository(
            [
                observation(
                    user_id=user_id,
                    tenant_id="tenant-a",
                    objective_namespace=(
                        "customer_service.support"
                    ),
                    objective_type="refund",
                    decision="approved",
                    result="achieved",
                ),
                observation(
                    user_id=user_id,
                    tenant_id="tenant-a",
                    objective_namespace=(
                        "customer_service.support"
                    ),
                    objective_type="cancel",
                    decision="approved",
                    result="failed",
                ),
            ]
        )
    )

    service = BusinessLearningSummaryService(
        db=SimpleNamespace(),
        repository=repository,
        policy=(
            BusinessLearningAggregationPolicy(
                minimum_effective_sample_size=1.0
            )
        ),
    )

    summaries = await service.summarize(
        user_id=user_id,
        tenant_id="tenant-a",
        objective_namespace=(
            "customer_service.support"
        ),
        objective_type="refund",
        decision="approved",
        window_hours=168,
    )

    assert len(summaries) == 1
    assert summaries[0].objective_type == "refund"
    assert summaries[0].achieved == 1

    call = repository.calls[0]
    assert call["window_hours"] == 168
    assert call["tenant_id"] == "tenant-a"
    assert call["objective_type"] == "refund"
    assert call["decision"] == "approved"
