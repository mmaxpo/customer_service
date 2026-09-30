from datetime import timedelta
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.capabilities.execution.health.evaluation import (
    CapabilityHealthEvaluationService,
)

from tests.runtime.contracts.test_capability_health_evaluation import (
    WINDOW_END,
    record_window,
    request,
)


@pytest.mark.asyncio
async def test_adjacent_same_recommendation_increments_streak():
    user_id = uuid4()
    second_end = WINDOW_END + timedelta(hours=1)

    async with SessionLocal() as db:
        await record_window(
            db=db,
            user_id=user_id,
            successes=19,
            failures=1,
            window_end=WINDOW_END,
        )

        service = CapabilityHealthEvaluationService(db)
        first = await service.evaluate(
            request=request(user_id=user_id)
        )

        await record_window(
            db=db,
            user_id=user_id,
            successes=19,
            failures=1,
            window_end=second_end,
        )

        second = await service.evaluate(
            request=request(
                user_id=user_id,
                window_end=second_end,
            )
        )

    assert first["qualifying_windows"] == 1
    assert second["qualifying_windows"] == 2


@pytest.mark.asyncio
async def test_temporal_gap_resets_streak():
    user_id = uuid4()
    gap_end = WINDOW_END + timedelta(hours=2)

    async with SessionLocal() as db:
        await record_window(
            db=db,
            user_id=user_id,
            successes=19,
            failures=1,
            window_end=WINDOW_END,
        )

        service = CapabilityHealthEvaluationService(db)
        await service.evaluate(
            request=request(user_id=user_id)
        )

        await record_window(
            db=db,
            user_id=user_id,
            successes=19,
            failures=1,
            window_end=gap_end,
        )

        result = await service.evaluate(
            request=request(
                user_id=user_id,
                window_end=gap_end,
            )
        )

    assert result["qualifying_windows"] == 1


@pytest.mark.asyncio
async def test_stale_window_does_not_mutate_state():
    user_id = uuid4()
    later_end = WINDOW_END + timedelta(hours=1)

    async with SessionLocal() as db:
        await record_window(
            db=db,
            user_id=user_id,
            successes=19,
            failures=1,
            window_end=later_end,
        )

        service = CapabilityHealthEvaluationService(db)
        latest = await service.evaluate(
            request=request(
                user_id=user_id,
                window_end=later_end,
            )
        )

        stale = await service.evaluate(
            request=request(
                user_id=user_id,
                window_end=WINDOW_END,
            )
        )

        state = await service.health_repo.get_state(
            user_id=user_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

    assert stale["status"] == "stale"
    assert stale["persisted"] is False
    assert state.version == (
        latest["persistence"]["state_version"]
    )


@pytest.mark.asyncio
async def test_insufficient_evidence_breaks_streak():
    user_id = uuid4()
    second_end = WINDOW_END + timedelta(hours=1)
    third_end = WINDOW_END + timedelta(hours=2)

    async with SessionLocal() as db:
        service = CapabilityHealthEvaluationService(db)

        await record_window(
            db=db,
            user_id=user_id,
            successes=19,
            failures=1,
            window_end=WINDOW_END,
        )
        first = await service.evaluate(
            request=request(user_id=user_id)
        )

        await record_window(
            db=db,
            user_id=user_id,
            successes=1,
            failures=0,
            window_end=second_end,
        )
        insufficient = await service.evaluate(
            request=request(
                user_id=user_id,
                window_end=second_end,
            )
        )

        await record_window(
            db=db,
            user_id=user_id,
            successes=19,
            failures=1,
            window_end=third_end,
        )
        third = await service.evaluate(
            request=request(
                user_id=user_id,
                window_end=third_end,
            )
        )

    assert first["qualifying_windows"] == 1
    assert insufficient["qualifying_windows"] == 0
    assert third["qualifying_windows"] == 1


@pytest.mark.asyncio
async def test_exact_window_retry_uses_same_evaluation_identity():
    user_id = uuid4()

    async with SessionLocal() as db:
        await record_window(
            db=db,
            user_id=user_id,
            successes=19,
            failures=1,
        )

        service = CapabilityHealthEvaluationService(db)
        first = await service.evaluate(
            request=request(user_id=user_id)
        )
        second = await service.evaluate(
            request=request(user_id=user_id)
        )

    assert first["persistence"]["inserted"] is True
    assert second["persistence"]["inserted"] is False
    assert (
        first["persistence"]["evaluation_key"]
        == second["persistence"]["evaluation_key"]
    )
