from types import SimpleNamespace
from uuid import uuid4

from app.domains.customer_service.services.event_subscriptions import (
    CustomerServiceEventSubscriptionService,
)


def _subscription(
    *,
    mode=None,
    priority=None,
    filters=None,
):
    meta = {}

    if mode is not None:
        meta["dispatch_mode"] = mode

    if priority is not None:
        meta["dispatch_priority"] = priority

    return SimpleNamespace(
        id=uuid4(),
        meta=meta,
        filters=filters or {},
    )


def _service():
    return CustomerServiceEventSubscriptionService.__new__(
        CustomerServiceEventSubscriptionService
    )


def test_fallback_runs_when_it_is_only_match():
    fallback = _subscription(
        mode="fallback",
        priority=0,
    )

    selected, skipped = (
        _service()._select_dispatch_subscriptions([fallback])
    )

    assert selected == [fallback]
    assert skipped == []


def test_specific_standard_suppresses_fallback():
    fallback = _subscription(
        mode="fallback",
        priority=0,
    )
    specific = _subscription(
        filters={"keywords": ["refund"]},
    )

    selected, skipped = (
        _service()._select_dispatch_subscriptions(
            [fallback, specific]
        )
    )

    assert selected == [specific]
    assert skipped == [
        {
            "subscription_id": str(fallback.id),
            "reason": "fallback_suppressed",
            "dispatch_mode": "fallback",
            "dispatch_priority": 0,
        }
    ]


def test_highest_priority_exclusive_wins():
    fallback = _subscription(
        mode="fallback",
        priority=0,
    )
    lower = _subscription(
        mode="exclusive",
        priority=50,
        filters={"keywords": ["refund"]},
    )
    winner = _subscription(
        mode="exclusive",
        priority=100,
        filters={"keywords": ["refund"]},
    )

    selected, skipped = (
        _service()._select_dispatch_subscriptions(
            [fallback, lower, winner]
        )
    )

    assert selected == [winner]

    skipped_by_id = {
        item["subscription_id"]: item
        for item in skipped
    }

    assert skipped_by_id[str(fallback.id)]["reason"] == (
        "fallback_suppressed"
    )
    assert skipped_by_id[str(lower.id)]["reason"] == (
        "exclusive_subscription_won"
    )


def test_equal_priority_exclusive_subscriptions_can_fan_out():
    first = _subscription(
        mode="exclusive",
        priority=100,
    )
    second = _subscription(
        mode="exclusive",
        priority=100,
    )

    selected, skipped = (
        _service()._select_dispatch_subscriptions(
            [first, second]
        )
    )

    assert selected == [first, second]
    assert skipped == []
