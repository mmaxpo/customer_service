from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.models.models import (
    CapabilityLearningObservationRecord,
    PlatformJob,
)
from app.platform.composition import (
    build_default_event_registry,
    build_default_job_registry,
)
from app.platform.events.event_store import (
    PlatformEventStore,
)
from app.platform.events.handlers.capabilities import (
    CAPABILITY_LEARNING_PROJECTION_JOB,
    enqueue_capability_learning_projection,
)
from app.runtime.capabilities.execution.jobs import (
    project_capability_learning_job,
)
from app.runtime.capabilities.execution.verification import (
    TASK_VERIFICATION_COMPLETED_EVENT,
    TaskVerificationMethod,
    TaskVerificationOutcome,
    TaskVerificationRepository,
    TaskVerificationRequest,
    TaskVerificationResult,
)


async def create_verification_event(
    *,
    db,
    user_id,
    retryable: bool = False,
):
    verification_id = f"automatic-learning-{uuid4()}"

    request = TaskVerificationRequest(
        verification_id=verification_id,
        capability_id=("ecommerce.orders.manage"),
        provider_id="shopify",
        provider_ref="shopify.order_action",
        action="refund",
        user_id=str(user_id),
        tenant_id="tenant-learning-auto",
        correlation_id="corr-learning-auto",
        workflow_run_id="run-learning-auto",
        task_id="task-learning-auto",
        metadata={
            "automatic": True,
            "source_event_id": ("capability-source-event"),
            "source_event_type": ("runtime.capability.execution.completed"),
        },
    )

    result = TaskVerificationResult(
        verification_id=verification_id,
        capability_id=request.capability_id,
        provider_id=request.provider_id,
        provider_ref=request.provider_ref,
        action=request.action,
        outcome=(
            TaskVerificationOutcome.INCONCLUSIVE
            if retryable
            else TaskVerificationOutcome.VERIFIED
        ),
        method=(TaskVerificationMethod.REMOTE_STATE),
        reason_code=("provider_temporarily_unavailable" if retryable else "verified"),
        summary=("Provider state unavailable." if retryable else "Outcome verified."),
        confidence=0.2 if retryable else 1.0,
        retryable=retryable,
        observed_outcome=({} if retryable else {"refund_completed": True}),
    )

    record = await TaskVerificationRepository(db).append_attempt(
        user_id=user_id,
        request=request,
        result=result,
        idempotency_key=(f"{verification_id}:attempt:1"),
    )
    await db.commit()
    await db.refresh(record)

    event = await PlatformEventStore(db).append(
        user_id=user_id,
        event_type=(TASK_VERIFICATION_COMPLETED_EVENT),
        source="runtime.task_verification",
        payload={
            "record_id": str(record.id),
            "verification_id": (record.verification_id),
            "attempt_number": (record.attempt_number),
            "capability_id": (record.capability_id),
            "provider_id": (record.provider_id),
            "provider_ref": (record.provider_ref),
            "action": record.action,
            "outcome": record.outcome,
            "method": record.method,
            "reason_code": (record.reason_code),
            "confidence": record.confidence,
            "retryable": record.retryable,
        },
        meta={
            "tenant_id": record.tenant_id,
            "correlation_id": (record.correlation_id),
            "workflow_run_id": (record.workflow_run_id),
            "task_id": record.task_id,
        },
    )

    return record, event


def test_learning_projection_handler_is_registered():

    handlers = build_default_event_registry().handlers_for(
        TASK_VERIFICATION_COMPLETED_EVENT
    )

    assert enqueue_capability_learning_projection in handlers


def test_learning_projection_job_is_registered():

    assert (
        build_default_job_registry().get(CAPABILITY_LEARNING_PROJECTION_JOB)
        is project_capability_learning_job
    )


@pytest.mark.asyncio
async def test_duplicate_verification_event_enqueues_one_learning_job():
    user_id = uuid4()

    async with SessionLocal() as db:
        _, event = await create_verification_event(
            db=db,
            user_id=user_id,
        )

        ctx = SimpleNamespace(
            db=db,
            event=event,
        )

        first = await enqueue_capability_learning_projection(
            event,
            ctx,
        )
        second = await enqueue_capability_learning_projection(
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
                        PlatformJob.job_type == (CAPABILITY_LEARNING_PROJECTION_JOB),
                        PlatformJob.idempotency_key
                        == (f"capability-learning-projection:{event.id}"),
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(rows) == 1


@pytest.mark.asyncio
async def test_learning_projection_job_persists_observation():
    user_id = uuid4()

    async with SessionLocal() as db:
        verification, event = await create_verification_event(
            db=db,
            user_id=user_id,
        )

        scheduled = await enqueue_capability_learning_projection(
            event,
            SimpleNamespace(
                db=db,
                event=event,
            ),
        )

        job = await db.get(
            PlatformJob,
            UUID(scheduled["enqueued_job_id"]),
        )

        result = await project_capability_learning_job(
            job.payload,
            SimpleNamespace(
                db=db,
                job=job,
                worker_id="test-worker",
            ),
        )

        assert result["inserted"] is True
        assert result["outcome"] == "verified"
        assert result["is_final"] is True

        row = await db.scalar(
            select(CapabilityLearningObservationRecord).where(
                CapabilityLearningObservationRecord.source_verification_record_id
                == verification.id
            )
        )

        assert row is not None
        assert row.user_id == user_id
        assert row.capability_id == (verification.capability_id)
        assert row.provider_id == "shopify"
        assert row.outcome == "verified"


@pytest.mark.asyncio
async def test_reprocessing_learning_job_is_idempotent():
    user_id = uuid4()

    async with SessionLocal() as db:
        verification, event = await create_verification_event(
            db=db,
            user_id=user_id,
        )

        scheduled = await enqueue_capability_learning_projection(
            event,
            SimpleNamespace(
                db=db,
                event=event,
            ),
        )

        job = await db.get(
            PlatformJob,
            UUID(scheduled["enqueued_job_id"]),
        )

        ctx = SimpleNamespace(
            db=db,
            job=job,
            worker_id="test-worker",
        )

        first = await project_capability_learning_job(
            job.payload,
            ctx,
        )
        second = await project_capability_learning_job(
            job.payload,
            ctx,
        )

        assert first["inserted"] is True
        assert second["inserted"] is False
        assert first["learning_observation_id"] == second["learning_observation_id"]

        rows = list(
            (
                await db.execute(
                    select(CapabilityLearningObservationRecord).where(
                        CapabilityLearningObservationRecord.source_verification_record_id
                        == verification.id
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(rows) == 1


@pytest.mark.asyncio
async def test_learning_job_rejects_cross_user_event():
    owner_id = uuid4()
    other_id = uuid4()

    async with SessionLocal() as db:
        _, event = await create_verification_event(
            db=db,
            user_id=owner_id,
        )

        fake_job = SimpleNamespace(
            user_id=other_id,
        )

        with pytest.raises(
            ValueError,
            match="ownership",
        ):
            await project_capability_learning_job(
                {"source_event_id": str(event.id)},
                SimpleNamespace(
                    db=db,
                    job=fake_job,
                    worker_id="test-worker",
                ),
            )
