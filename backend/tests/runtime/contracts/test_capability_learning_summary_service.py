from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.capabilities.execution.learning import (
    CapabilityLearningAggregationPolicy,
    CapabilityLearningInterpretation,
    CapabilityLearningSummaryService,
)


class FakeLearningRepository:
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
            "capability_id",
            "provider_id",
            "provider_ref",
            "action",
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
    capability_id,
    provider_id,
    provider_ref,
    tenant_id,
    action,
    outcome,
    confidence=1.0,
    is_final=True,
    retryable=False,
    evidence_count=1,
):
    return SimpleNamespace(
        user_id=user_id,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
        tenant_id=tenant_id,
        action=action,
        outcome=outcome,
        confidence=confidence,
        is_final=is_final,
        retryable=retryable,
        evidence_summary_json={
            "count": evidence_count,
            "items": [],
        },
    )


@pytest.mark.asyncio
async def test_learning_summary_service_groups_by_full_scope():
    user_id = uuid4()

    repository = FakeLearningRepository(
        [
            observation(
                user_id=user_id,
                capability_id=(
                    "ecommerce.orders.manage"
                ),
                provider_id="shopify",
                provider_ref=(
                    "shopify.order_action"
                ),
                tenant_id="tenant-a",
                action="refund",
                outcome="verified",
            ),
            observation(
                user_id=user_id,
                capability_id=(
                    "ecommerce.orders.manage"
                ),
                provider_id="shopify",
                provider_ref=(
                    "shopify.order_action"
                ),
                tenant_id="tenant-a",
                action="refund",
                outcome="failed",
            ),
            observation(
                user_id=user_id,
                capability_id=(
                    "ecommerce.orders.manage"
                ),
                provider_id="shopify",
                provider_ref=(
                    "shopify.order_action"
                ),
                tenant_id="tenant-a",
                action="cancel",
                outcome="verified",
            ),
        ]
    )

    service = CapabilityLearningSummaryService(
        db=SimpleNamespace(),
        repository=repository,
        policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=1.0
            )
        ),
    )

    summaries = await service.summarize(
        user_id=user_id,
        window_hours=24,
    )

    assert len(summaries) == 2

    refund = next(
        item
        for item in summaries
        if item.action == "refund"
    )
    cancel = next(
        item
        for item in summaries
        if item.action == "cancel"
    )

    assert refund.total_observations == 2
    assert refund.verified == 1
    assert refund.failed == 1
    assert refund.estimated_success_rate == 0.5

    assert cancel.total_observations == 1
    assert cancel.verified == 1
    assert cancel.estimated_success_rate == 1.0


@pytest.mark.asyncio
async def test_learning_summary_service_preserves_user_scope():
    current_user_id = uuid4()
    other_user_id = uuid4()

    repository = FakeLearningRepository(
        [
            observation(
                user_id=current_user_id,
                capability_id="capability.a",
                provider_id="provider",
                provider_ref="provider.action",
                tenant_id=None,
                action="execute",
                outcome="verified",
            ),
            observation(
                user_id=other_user_id,
                capability_id="capability.b",
                provider_id="provider",
                provider_ref="provider.action",
                tenant_id=None,
                action="execute",
                outcome="failed",
            ),
        ]
    )

    service = CapabilityLearningSummaryService(
        db=SimpleNamespace(),
        repository=repository,
        policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=1.0
            )
        ),
    )

    summaries = await service.summarize(
        user_id=current_user_id,
    )

    assert len(summaries) == 1
    assert (
        summaries[0].capability_id
        == "capability.a"
    )
    assert (
        repository.calls[0]["user_id"]
        == current_user_id
    )


@pytest.mark.asyncio
async def test_learning_summary_service_applies_filters():
    user_id = uuid4()

    repository = FakeLearningRepository(
        [
            observation(
                user_id=user_id,
                capability_id="capability.a",
                provider_id="provider-a",
                provider_ref="provider-a.action",
                tenant_id="tenant-a",
                action="refund",
                outcome="verified",
            ),
            observation(
                user_id=user_id,
                capability_id="capability.a",
                provider_id="provider-b",
                provider_ref="provider-b.action",
                tenant_id="tenant-a",
                action="refund",
                outcome="failed",
            ),
        ]
    )

    service = CapabilityLearningSummaryService(
        db=SimpleNamespace(),
        repository=repository,
        policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=1.0
            )
        ),
    )

    summaries = await service.summarize(
        user_id=user_id,
        tenant_id="tenant-a",
        capability_id="capability.a",
        provider_id="provider-a",
        action="refund",
        window_hours=168,
    )

    assert len(summaries) == 1
    assert summaries[0].provider_id == "provider-a"
    assert summaries[0].interpretation == (
        CapabilityLearningInterpretation
        .POSITIVE
    )

    call = repository.calls[0]
    assert call["window_hours"] == 168
    assert call["provider_id"] == "provider-a"
