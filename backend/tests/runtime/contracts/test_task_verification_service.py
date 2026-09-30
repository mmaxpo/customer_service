from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.models.models import (
    PlatformEvent,
    TaskVerificationRecord,
)
from app.runtime.capabilities.execution.verification import (
    TASK_OUTCOME_INCONCLUSIVE_EVENT,
    TASK_OUTCOME_VERIFIED_EVENT,
    TASK_VERIFICATION_COMPLETED_EVENT,
    TASK_VERIFICATION_FAILED_EVENT,
    TaskVerificationRequest,
    TaskVerificationService,
)


class CountingShopify:
    def __init__(
        self,
        *,
        cancelled_at=(
            "2026-07-18T12:00:00Z"
        ),
    ):
        self.cancelled_at = cancelled_at
        self.calls = 0

    async def get_order_fresh(
        self,
        *,
        user_id,
        order_ref,
    ):
        self.calls += 1

        return {
            "id": "4001",
            "name": order_ref,
            "cancelled_at": (
                self.cancelled_at
            ),
            "financial_status": "voided",
            "fulfillment_status": None,
        }


class ExplodingShopify:
    async def get_order_fresh(
        self,
        *,
        user_id,
        order_ref,
    ):
        raise RuntimeError(
            "secret remote failure detail"
        )


def services_with_shopify(shopify):
    return SimpleNamespace(
        business=SimpleNamespace(
            shopify=shopify
        )
    )


def cancellation_request(
    *,
    user_id,
    verification_id,
):
    return TaskVerificationRequest(
        verification_id=verification_id,
        capability_id=(
            "ecommerce.orders.manage"
        ),
        provider_id="shopify",
        provider_ref=(
            "shopify.order_action"
        ),
        action="cancel",
        user_id=str(user_id),
        tenant_id="tenant-service",
        correlation_id=(
            f"correlation-{uuid4()}"
        ),
        workflow_run_id="run-service",
        task_id="task-service",
        inputs={
            "action": "cancel",
            "order_ref": "#4001",
        },
        expected_outcome={
            "order_cancelled": True,
        },
        execution_output={
            "status": "cancelled",
        },
    )


@pytest.mark.asyncio
async def test_verification_service_persists_record_and_events_atomically():
    user_id = uuid4()
    verification_id = f"verify-{uuid4()}"
    shopify = CountingShopify()

    async with SessionLocal() as db:
        execution = await (
            TaskVerificationService(
                db,
                services=(
                    services_with_shopify(
                        shopify
                    )
                ),
            )
            .verify(
                user_id=user_id,
                request=cancellation_request(
                    user_id=user_id,
                    verification_id=(
                        verification_id
                    ),
                ),
                idempotency_key=(
                    f"verification:{verification_id}:1"
                ),
            )
        )

        assert execution.created is True
        assert execution.attempt_number == 1
        assert (
            execution.result.outcome.value
            == "verified"
        )
        assert shopify.calls == 1

    async with SessionLocal() as db:
        records = list(
            (
                await db.execute(
                    select(
                        TaskVerificationRecord
                    ).where(
                        TaskVerificationRecord
                        .user_id
                        == user_id,
                        TaskVerificationRecord
                        .verification_id
                        == verification_id,
                    )
                )
            )
            .scalars()
            .all()
        )

        events = list(
            (
                await db.execute(
                    select(PlatformEvent)
                    .where(
                        PlatformEvent.user_id
                        == user_id,
                        PlatformEvent.source
                        == (
                            "runtime."
                            "task_verification"
                        ),
                        PlatformEvent.payload[
                            "verification_id"
                        ].astext
                        == verification_id,
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(records) == 1
        assert {
            event.event_type
            for event in events
        } == {
            TASK_VERIFICATION_COMPLETED_EVENT,
            TASK_OUTCOME_VERIFIED_EVENT,
        }

        payload_text = str(
            [
                event.payload
                for event in events
            ]
        )

        assert "#4001" not in payload_text
        assert "execution_output" not in payload_text


@pytest.mark.asyncio
async def test_idempotent_replay_skips_remote_verifier_and_events():
    user_id = uuid4()
    verification_id = f"verify-{uuid4()}"
    key = f"verification:{verification_id}:same"
    shopify = CountingShopify()
    request = cancellation_request(
        user_id=user_id,
        verification_id=verification_id,
    )

    async with SessionLocal() as db:
        service = TaskVerificationService(
            db,
            services=services_with_shopify(
                shopify
            ),
        )

        first = await service.verify(
            user_id=user_id,
            request=request,
            idempotency_key=key,
        )
        second = await service.verify(
            user_id=user_id,
            request=request,
            idempotency_key=key,
        )

        assert first.created is True
        assert second.created is False
        assert second.record_id == first.record_id
        assert shopify.calls == 1

    async with SessionLocal() as db:
        records = list(
            (
                await db.execute(
                    select(
                        TaskVerificationRecord
                    ).where(
                        TaskVerificationRecord
                        .user_id
                        == user_id,
                        TaskVerificationRecord
                        .verification_id
                        == verification_id,
                    )
                )
            )
            .scalars()
            .all()
        )

        events = list(
            (
                await db.execute(
                    select(PlatformEvent)
                    .where(
                        PlatformEvent.user_id
                        == user_id,
                        PlatformEvent.source
                        == (
                            "runtime."
                            "task_verification"
                        ),
                        PlatformEvent.payload[
                            "verification_id"
                        ].astext
                        == verification_id,
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(records) == 1
        assert len(events) == 2


@pytest.mark.asyncio
async def test_unhandled_verifier_error_becomes_durable_retryable_result():
    user_id = uuid4()
    verification_id = f"verify-{uuid4()}"

    async with SessionLocal() as db:
        execution = await (
            TaskVerificationService(
                db,
                services=(
                    services_with_shopify(
                        ExplodingShopify()
                    )
                ),
            )
            .verify(
                user_id=user_id,
                request=cancellation_request(
                    user_id=user_id,
                    verification_id=(
                        verification_id
                    ),
                ),
                idempotency_key=(
                    f"verification:{verification_id}:1"
                ),
            )
        )

        assert (
            execution.result.outcome.value
            == "inconclusive"
        )
        assert (
            execution.result.reason_code
            == "cancel_remote_observation_failed"
        )
        assert execution.result.retryable is True

    async with SessionLocal() as db:
        events = list(
            (
                await db.execute(
                    select(PlatformEvent)
                    .where(
                        PlatformEvent.user_id
                        == user_id,
                        PlatformEvent.source
                        == (
                            "runtime."
                            "task_verification"
                        ),
                        PlatformEvent.payload[
                            "verification_id"
                        ].astext
                        == verification_id,
                    )
                )
            )
            .scalars()
            .all()
        )

        # Shopify verifier converts provider read errors into an ordinary,
        # retryable inconclusive result, so orchestration itself completed.
        assert {
            event.event_type
            for event in events
        } == {
            TASK_VERIFICATION_COMPLETED_EVENT,
            TASK_OUTCOME_INCONCLUSIVE_EVENT,
        }

        assert (
            "secret remote failure detail"
            not in str(events)
        )


@pytest.mark.asyncio
async def test_registry_failure_persists_failed_lifecycle_event():
    user_id = uuid4()
    verification_id = f"verify-{uuid4()}"
    request = cancellation_request(
        user_id=user_id,
        verification_id=verification_id,
    ).model_copy(
        update={
            "action": "unknown_action",
            "inputs": {
                "action": "unknown_action",
                "order_ref": "#4001",
            },
        }
    )

    async with SessionLocal() as db:
        execution = await (
            TaskVerificationService(db)
            .verify(
                user_id=user_id,
                request=request,
                idempotency_key=(
                    f"verification:{verification_id}:1"
                ),
            )
        )

        assert (
            execution.result.reason_code
            == "verifier_execution_failed"
        )
        assert (
            execution.result.outcome.value
            == "inconclusive"
        )

    async with SessionLocal() as db:
        events = list(
            (
                await db.execute(
                    select(PlatformEvent)
                    .where(
                        PlatformEvent.user_id
                        == user_id,
                        PlatformEvent.source
                        == (
                            "runtime."
                            "task_verification"
                        ),
                        PlatformEvent.payload[
                            "verification_id"
                        ].astext
                        == verification_id,
                    )
                )
            )
            .scalars()
            .all()
        )

        assert {
            event.event_type
            for event in events
        } == {
            TASK_VERIFICATION_FAILED_EVENT,
            TASK_OUTCOME_INCONCLUSIVE_EVENT,
        }


@pytest.mark.asyncio
async def test_record_and_events_roll_back_together(
    monkeypatch,
):
    from app.runtime.capabilities.execution.verification import (
        events as event_module,
    )

    user_id = uuid4()
    verification_id = f"verify-{uuid4()}"
    original_publish = (
        event_module
        .TaskVerificationLifecycleEvents
        .business_outcome
    )

    async def fail_business_event(
        self,
        **kwargs,
    ):
        raise RuntimeError(
            "event publication failed"
        )

    monkeypatch.setattr(
        event_module
        .TaskVerificationLifecycleEvents,
        "business_outcome",
        fail_business_event,
    )

    async with SessionLocal() as db:
        with pytest.raises(
            RuntimeError,
            match="event publication failed",
        ):
            await (
                TaskVerificationService(
                    db,
                    services=(
                        services_with_shopify(
                            CountingShopify()
                        )
                    ),
                )
                .verify(
                    user_id=user_id,
                    request=cancellation_request(
                        user_id=user_id,
                        verification_id=(
                            verification_id
                        ),
                    ),
                    idempotency_key=(
                        f"verification:"
                        f"{verification_id}:1"
                    ),
                )
            )

    monkeypatch.setattr(
        event_module
        .TaskVerificationLifecycleEvents,
        "business_outcome",
        original_publish,
    )

    async with SessionLocal() as db:
        record = await db.execute(
            select(TaskVerificationRecord)
            .where(
                TaskVerificationRecord.user_id
                == user_id,
                TaskVerificationRecord
                .verification_id
                == verification_id,
            )
        )
        event = await db.execute(
            select(PlatformEvent)
            .where(
                PlatformEvent.user_id
                == user_id,
                PlatformEvent.source
                == (
                    "runtime.task_verification"
                ),
                PlatformEvent.payload[
                    "verification_id"
                ].astext
                == verification_id,
            )
        )

        assert (
            record.scalar_one_or_none()
            is None
        )
        assert (
            event.scalar_one_or_none()
            is None
        )


@pytest.mark.asyncio
async def test_service_rejects_cross_user_request():
    authenticated_user_id = uuid4()
    request_user_id = uuid4()

    async with SessionLocal() as db:
        with pytest.raises(
            ValueError,
            match="does not match authenticated user",
        ):
            await (
                TaskVerificationService(db)
                .verify(
                    user_id=(
                        authenticated_user_id
                    ),
                    request=(
                        cancellation_request(
                            user_id=request_user_id,
                            verification_id=(
                                f"verify-{uuid4()}"
                            ),
                        )
                    ),
                    idempotency_key=(
                        f"verification:{uuid4()}"
                    ),
                )
            )
