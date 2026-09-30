from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.events.handlers import (
    OBJECTIVE_RESOLUTION_ASSESSED_EVENT,
    enqueue_customer_support_objective_learning,
)
from app.domains.customer_service.jobs.handlers import (
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_JOB,
    record_customer_support_objective_learning_job,
)
from app.models.models import (
    ObjectiveLearningExperienceRecord,
    ObjectiveResolutionRecord,
    PlatformJob,
)
from app.platform.composition import (
    build_default_event_registry,
    build_default_job_registry,
)
from app.platform.events.event_store import (
    PlatformEventStore,
)


async def _create_resolution_event(
    *,
    user_id: UUID,
    is_terminal: bool,
) -> tuple[UUID, UUID]:
    async with SessionLocal() as db:
        source_event = await PlatformEventStore(db).append(
            user_id=user_id,
            event_type=("customer_service.support.outcome.evaluated"),
            source="test",
            payload={
                "fixture": ("objective_learning_event_job_bridge"),
            },
            meta={},
            commit=False,
        )

        resolution = ObjectiveResolutionRecord(
            source_event_id=source_event.id,
            user_id=user_id,
            tenant_id=None,
            objective_namespace=("customer_service.support"),
            objective_type="multi_operation",
            objective_ref=str(uuid4()),
            objective_version=1,
            source_outcome_ref=str(uuid4()),
            outcome_version=1,
            source_evaluation_ref=str(uuid4()),
            evaluation_version=1,
            projection_version=1,
            assessment_schema_version=("objective_resolution.v1"),
            workflow_run_id=str(uuid4()),
            status=("achieved" if is_terminal else "partially_achieved"),
            reason_code=(
                "all_operations_achieved" if is_terminal else "operations_pending"
            ),
            summary=(
                "Objective is terminal."
                if is_terminal
                else "Objective remains in progress."
            ),
            confidence=0.95,
            is_terminal=is_terminal,
            operation_count=1,
            achieved_operation_count=(1 if is_terminal else 0),
            unresolved_operation_count=(0 if is_terminal else 1),
            failed_operation_count=0,
            pending_operation_count=(0 if is_terminal else 1),
            unknown_operation_count=0,
            not_executed_operation_count=0,
            assessment_json={
                "schema_version": ("objective_resolution.v1"),
            },
        )
        db.add(resolution)
        await db.flush()

        event = await PlatformEventStore(db).append(
            user_id=user_id,
            event_type=(OBJECTIVE_RESOLUTION_ASSESSED_EVENT),
            source="test",
            payload={
                "resolution_record_id": str(resolution.id),
                "objective_namespace": (resolution.objective_namespace),
                "objective_type": (resolution.objective_type),
                "objective_ref": (resolution.objective_ref),
                "objective_version": (resolution.objective_version),
                "status": resolution.status,
                "is_terminal": (resolution.is_terminal),
            },
            meta={
                "tenant_id": None,
                "workflow_run_id": str(resolution.workflow_run_id),
            },
            commit=False,
        )

        await db.commit()

        return resolution.id, event.id


def test_learning_event_and_job_handlers_registered():
    handlers = build_default_event_registry().handlers_for(
        OBJECTIVE_RESOLUTION_ASSESSED_EVENT
    )

    assert enqueue_customer_support_objective_learning in handlers
    assert (
        build_default_job_registry().get(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_JOB)
        is record_customer_support_objective_learning_job
    )


@pytest.mark.asyncio
async def test_non_terminal_resolution_does_not_schedule_learning():
    user_id = uuid4()
    resolution_id, event_id = await _create_resolution_event(
        user_id=user_id,
        is_terminal=False,
    )

    async with SessionLocal() as db:
        event = await PlatformEventStore(db).get(event_id)

        result = await enqueue_customer_support_objective_learning(
            event,
            SimpleNamespace(db=db),
        )

        await db.commit()

    assert result == {
        "scheduled": False,
        "reason": "resolution_is_not_terminal",
        "source_event_id": str(event_id),
        "resolution_record_id": str(resolution_id),
    }

    async with SessionLocal() as db:
        jobs = list(
            (
                await db.execute(
                    select(PlatformJob).where(
                        PlatformJob.job_type
                        == (CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_JOB),
                        PlatformJob.user_id == user_id,
                    )
                )
            )
            .scalars()
            .all()
        )

    assert jobs == []


@pytest.mark.asyncio
async def test_duplicate_terminal_event_delivery_reuses_learning_job():
    user_id = uuid4()
    resolution_id, event_id = await _create_resolution_event(
        user_id=user_id,
        is_terminal=True,
    )

    async with SessionLocal() as db:
        event = await PlatformEventStore(db).get(event_id)

        first = await enqueue_customer_support_objective_learning(
            event,
            SimpleNamespace(db=db),
        )
        second = await enqueue_customer_support_objective_learning(
            event,
            SimpleNamespace(db=db),
        )

        await db.commit()

    assert first["job_id"] == second["job_id"]
    assert first["resolution_record_id"] == str(resolution_id)

    async with SessionLocal() as db:
        jobs = list(
            (
                await db.execute(
                    select(PlatformJob).where(
                        PlatformJob.job_type
                        == (CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_JOB),
                        PlatformJob.user_id == user_id,
                    )
                )
            )
            .scalars()
            .all()
        )

    assert len(jobs) == 1
    assert jobs[0].payload == {
        "source_event_id": str(event_id),
        "resolution_record_id": str(resolution_id),
    }


@pytest.mark.asyncio
async def test_learning_job_rejects_owner_mismatch():
    owner_id = uuid4()
    other_id = uuid4()

    _, event_id = await _create_resolution_event(
        user_id=owner_id,
        is_terminal=True,
    )

    async with SessionLocal() as db:
        event = await PlatformEventStore(db).get(event_id)

        scheduled = await enqueue_customer_support_objective_learning(
            event,
            SimpleNamespace(db=db),
        )
        await db.commit()

        job = await db.get(
            PlatformJob,
            UUID(scheduled["job_id"]),
        )
        job.user_id = other_id

        with pytest.raises(
            ValueError,
            match="ownership does not match",
        ):
            await record_customer_support_objective_learning_job(
                job.payload,
                SimpleNamespace(
                    db=db,
                    job=job,
                ),
            )


@pytest.mark.asyncio
async def test_learning_job_rejects_resolution_identity_mismatch():
    user_id = uuid4()
    _, event_id = await _create_resolution_event(
        user_id=user_id,
        is_terminal=True,
    )

    async with SessionLocal() as db:
        event = await PlatformEventStore(db).get(event_id)

        scheduled = await enqueue_customer_support_objective_learning(
            event,
            SimpleNamespace(db=db),
        )
        await db.commit()

        job = await db.get(
            PlatformJob,
            UUID(scheduled["job_id"]),
        )
        job.payload = {
            **job.payload,
            "resolution_record_id": str(uuid4()),
        }

        with pytest.raises(
            ValueError,
            match=("resolution identity does not match source event"),
        ):
            await record_customer_support_objective_learning_job(
                job.payload,
                SimpleNamespace(
                    db=db,
                    job=job,
                ),
            )


@pytest.mark.asyncio
async def test_learning_job_calls_canonical_recording_service(
    monkeypatch,
):
    user_id = uuid4()
    resolution_id, event_id = await _create_resolution_event(
        user_id=user_id,
        is_terminal=True,
    )
    learning_id = uuid4()
    calls: list[dict] = []

    class FakeRecordingService:
        def __init__(self, db):
            self.db = db

        async def record_for_resolution(
            self,
            *,
            user_id,
            resolution_record_id,
            tenant_id=None,
        ):
            calls.append(
                {
                    "user_id": user_id,
                    "resolution_record_id": (resolution_record_id),
                    "tenant_id": tenant_id,
                }
            )

            record = SimpleNamespace(
                id=learning_id,
                profile_ref=("customer_service.support.objective_learning"),
                profile_version=1,
                informational_only=True,
                authorizes_execution=False,
            )

            return SimpleNamespace(
                record=record,
                created=True,
            )

    monkeypatch.setattr(
        "app.domains.customer_service.jobs.handlers."
        "CustomerSupportObjectiveLearningRecordingService",
        FakeRecordingService,
    )

    async with SessionLocal() as db:
        event = await PlatformEventStore(db).get(event_id)

        scheduled = await enqueue_customer_support_objective_learning(
            event,
            SimpleNamespace(db=db),
        )
        await db.commit()

        job = await db.get(
            PlatformJob,
            UUID(scheduled["job_id"]),
        )

        result = await record_customer_support_objective_learning_job(
            job.payload,
            SimpleNamespace(
                db=db,
                job=job,
            ),
        )

    assert calls == [
        {
            "user_id": user_id,
            "resolution_record_id": (resolution_id),
            "tenant_id": None,
        }
    ]

    assert result == {
        "status": "recorded",
        "source_event_id": str(event_id),
        "resolution_record_id": str(resolution_id),
        "learning_experience_id": str(learning_id),
        "profile_ref": ("customer_service.support.objective_learning"),
        "profile_version": 1,
        "created": True,
        "informational_only": True,
        "authorizes_execution": False,
    }

    async with SessionLocal() as db:
        experiences = list(
            (
                await db.execute(
                    select(ObjectiveLearningExperienceRecord).where(
                        ObjectiveLearningExperienceRecord.user_id == user_id
                    )
                )
            )
            .scalars()
            .all()
        )

    # The fake service proves composition without fabricating
    # canonical outcome/evaluation/review-plan lineage.
    assert experiences == []
