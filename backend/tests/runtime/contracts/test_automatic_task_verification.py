from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.models.models import (
    PlatformJob,
    TaskVerificationRecord,
)
from app.platform.composition import (
    build_default_event_registry,
    build_default_job_registry,
)
from app.platform.events.event_store import (
    PlatformEventStore,
)
from app.platform.events.handlers.capabilities import (
    CAPABILITY_TASK_VERIFICATION_JOB,
    enqueue_capability_task_verification,
)
from app.platform.jobs.worker import JobWorker
from app.runtime.capabilities.execution.outcomes import (
    build_capability_execution_outcome,
)
from app.runtime.capabilities.execution.reporting import (
    CAPABILITY_EXECUTION_COMPLETED_EVENT,
)
from app.runtime.capabilities.models import (
    CapabilityInvocation,
    CapabilityInvocationStatus,
    CapabilityResult,
)


def build_refund_outcome():
    invocation = CapabilityInvocation(
        capability_id=("ecommerce.orders.manage"),
        inputs={
            "action": "refund",
            "order_ref": "#7001",
            "amount": "15.00",
            "note": "private note",
            "new_address": {
                "address1": "private address",
            },
            "idempotency_key": ("provider-secret-key"),
        },
        user_id=uuid4(),
        correlation_id=(f"automatic-{uuid4()}"),
        metadata={
            "workflow_run_id": "run-auto",
            "task_id": "task-auto",
        },
    )

    result = CapabilityResult(
        status=CapabilityInvocationStatus.OK,
        capability_id=(invocation.capability_id),
        output={
            "status": "prepared",
            "payload": {
                "status": "prepared",
                "order_id": "7001",
                "amount": "15.00",
            },
        },
        metadata={
            "resolved_capability_id": ("ecommerce.orders.manage"),
            "selected_provider_id": ("shopify"),
            "provider_ref": ("shopify.order_action"),
        },
    )

    return build_capability_execution_outcome(
        invocation=invocation,
        result=result,
        tenant_id="tenant-auto",
    )


def test_outcome_contains_minimal_verification_context():
    outcome = build_refund_outcome()

    context = outcome.verification_context

    assert context is not None
    assert context["action"] == "refund"
    assert context["inputs"] == {
        "action": "refund",
        "order_ref": "#7001",
        "amount": "15.00",
    }
    assert context["expected_outcome"]["refund_completed"] is False

    serialized = str(context)

    assert "private note" not in serialized
    assert "private address" not in serialized
    assert "provider-secret-key" not in serialized


def test_failed_or_read_only_execution_has_no_verification_context():
    invocation = CapabilityInvocation(
        capability_id=("ecommerce.orders.get"),
        inputs={
            "order_ref": "#7002",
        },
        user_id=uuid4(),
    )

    result = CapabilityResult(
        status=CapabilityInvocationStatus.OK,
        capability_id=(invocation.capability_id),
        output={"id": "7002"},
        metadata={
            "resolved_capability_id": ("ecommerce.orders.get"),
            "selected_provider_id": ("shopify"),
            "provider_ref": ("shopify.get_order"),
        },
    )

    outcome = build_capability_execution_outcome(
        invocation=invocation,
        result=result,
    )

    assert outcome.verification_context is None


def test_automatic_verification_handlers_are_registered():
    event_handlers = build_default_event_registry().handlers_for(
        CAPABILITY_EXECUTION_COMPLETED_EVENT
    )

    assert any(
        handler.__name__ == ("enqueue_capability_task_verification")
        for handler in event_handlers
    )

    assert (
        build_default_job_registry().get(CAPABILITY_TASK_VERIFICATION_JOB) is not None
    )


@pytest.mark.asyncio
async def test_duplicate_event_delivery_enqueues_one_job():
    user_id = uuid4()
    outcome = build_refund_outcome()

    async with SessionLocal() as db:
        event = await PlatformEventStore(db).append(
            user_id=user_id,
            event_type=(CAPABILITY_EXECUTION_COMPLETED_EVENT),
            source="runtime.capabilities",
            payload={
                "requested_capability_id": (outcome.requested_capability_id),
                "resolved_capability_id": (outcome.resolved_capability_id),
                "status": (outcome.status.value),
                "ok": outcome.ok,
                "selected_provider_id": (outcome.selected_provider_id),
                "provider_ref": (outcome.provider_ref),
                "verification_context": (outcome.verification_context),
            },
            meta={
                "correlation_id": (outcome.correlation_id),
                "tenant_id": "tenant-auto",
                "workflow_run_id": "run-auto",
                "invocation_metadata": {
                    "task_id": "task-auto",
                },
            },
        )

        ctx = SimpleNamespace(
            db=db,
            event=event,
        )

        first = await enqueue_capability_task_verification(
            event,
            ctx,
        )
        second = await enqueue_capability_task_verification(
            event,
            ctx,
        )

        assert first["scheduled"] is True
        assert second["scheduled"] is True
        assert first["enqueued_job_id"] == second["enqueued_job_id"]

        rows = list(
            (
                await db.execute(
                    select(PlatformJob).where(
                        PlatformJob.job_type == (CAPABILITY_TASK_VERIFICATION_JOB),
                        PlatformJob.idempotency_key
                        == (f"capability-task-verification:{event.id}"),
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(rows) == 1


@pytest.mark.asyncio
async def test_automatic_refund_verification_job_persists_attempt():
    user_id = uuid4()
    outcome = build_refund_outcome()

    async with SessionLocal() as db:
        event = await PlatformEventStore(db).append(
            user_id=user_id,
            event_type=(CAPABILITY_EXECUTION_COMPLETED_EVENT),
            source="runtime.capabilities",
            payload={
                "requested_capability_id": (outcome.requested_capability_id),
                "resolved_capability_id": (outcome.resolved_capability_id),
                "status": (outcome.status.value),
                "ok": True,
                "selected_provider_id": ("shopify"),
                "provider_ref": ("shopify.order_action"),
                "verification_context": (outcome.verification_context),
            },
            meta={
                "correlation_id": (outcome.correlation_id),
                "tenant_id": "tenant-auto",
                "workflow_run_id": "run-auto",
                "invocation_metadata": {
                    "task_id": "task-auto",
                },
            },
        )

        scheduled = await enqueue_capability_task_verification(
            event,
            SimpleNamespace(
                db=db,
                event=event,
            ),
        )

        job = await JobWorker(
            db,
            worker_id=("automatic-verification-worker"),
        ).run_once(job_id=scheduled["enqueued_job_id"])

        assert job is not None
        assert job.status == "succeeded"
        assert job.result["outcome"] == "partially_verified"

    async with SessionLocal() as db:
        rows = list(
            (
                await db.execute(
                    select(TaskVerificationRecord).where(
                        TaskVerificationRecord.user_id == user_id,
                        TaskVerificationRecord.correlation_id == outcome.correlation_id,
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(rows) == 1
        assert rows[0].attempt_number == 1
        assert rows[0].outcome == "partially_verified"
        assert rows[0].workflow_run_id == "run-auto"
        assert rows[0].task_id == "task-auto"


@pytest.mark.asyncio
async def test_reprocessing_same_job_uses_same_verification_attempt():
    user_id = uuid4()
    outcome = build_refund_outcome()

    async with SessionLocal() as db:
        event = await PlatformEventStore(db).append(
            user_id=user_id,
            event_type=(CAPABILITY_EXECUTION_COMPLETED_EVENT),
            source="runtime.capabilities",
            payload={
                "requested_capability_id": (outcome.requested_capability_id),
                "resolved_capability_id": (outcome.resolved_capability_id),
                "ok": True,
                "status": "succeeded",
                "selected_provider_id": ("shopify"),
                "provider_ref": ("shopify.order_action"),
                "verification_context": (outcome.verification_context),
            },
            meta={
                "correlation_id": (outcome.correlation_id),
                "tenant_id": "tenant-auto",
                "invocation_metadata": {},
            },
        )

        scheduled = await enqueue_capability_task_verification(
            event,
            SimpleNamespace(
                db=db,
                event=event,
            ),
        )

        handler = build_default_job_registry().get(CAPABILITY_TASK_VERIFICATION_JOB)
        assert handler is not None

        job = await db.get(
            PlatformJob,
            scheduled["enqueued_job_id"],
        )
        assert job is not None

        ctx = SimpleNamespace(
            db=db,
            job=job,
            worker_id="manual-replay",
        )

        first = await handler(
            job.payload,
            ctx,
        )
        second = await handler(
            job.payload,
            ctx,
        )

        assert first["created"] is True
        assert second["created"] is False
        assert first["record_id"] == second["record_id"]

    async with SessionLocal() as db:
        rows = list(
            (
                await db.execute(
                    select(TaskVerificationRecord).where(
                        TaskVerificationRecord.user_id == user_id,
                        TaskVerificationRecord.correlation_id == outcome.correlation_id,
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(rows) == 1
