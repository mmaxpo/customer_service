from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.events.handlers import (
    enqueue_customer_support_objective_resolution,
)
from app.domains.customer_service.jobs.handlers import (
    CUSTOMER_SUPPORT_OBJECTIVE_RESOLUTION_JOB,
    project_customer_support_objective_resolution_job,
)
from app.domains.customer_service.models.outcomes import (
    CustomerSupportOutcomeEvaluationRecord,
    CustomerSupportOutcomeRecord,
)
from app.domains.customer_service.services.support.outcome.customer_support_outcome_evaluation_service import (
    SUPPORT_OUTCOME_EVALUATED_EVENT,
)
from app.models.models import (
    ObjectiveResolutionRecord,
    PlatformEvent,
    PlatformJob,
)
from app.platform.composition import (
    build_default_event_registry,
    build_default_job_registry,
)
from app.platform.events.event_store import (
    PlatformEventStore,
)
from app.runtime.objectives.resolution import (
    OBJECTIVE_RESOLUTION_ASSESSED_EVENT,
)


async def _create_source(
    *,
    user_id: UUID,
    statuses: list[str],
    result: str,
):
    async with SessionLocal() as db:
        outcome = CustomerSupportOutcomeRecord(
            user_id=user_id,
            review_plan_id=str(uuid4()),
            workflow_run_id=uuid4(),
            chat_session_id=uuid4(),
            conversation_id=uuid4(),
            objective_namespace=("customer_service.support"),
            objective_ref=str(uuid4()),
            source_objective_version=1,
            outcome_version=1,
            objective_type="multi_operation",
            order_ref="#1001",
            decision="approved",
            status=(statuses[0] if len(set(statuses)) == 1 else "mixed"),
            operation_count=len(statuses),
            customer_message="Recorded.",
            operations_json=[
                {
                    "operation_ref": (f"operation-{index}"),
                    "operation_type": ("whole_refund" if index == 1 else "replacement"),
                    "status": status,
                }
                for index, status in enumerate(
                    statuses,
                    start=1,
                )
            ],
            outcome_json={},
        )
        db.add(outcome)
        await db.flush()

        achieved = statuses.count("completed")
        failed = statuses.count("failed")
        pending = sum(status in {"prepared", "submitted"} for status in statuses)
        unknown = statuses.count("unknown")
        not_executed = statuses.count("rejected")

        evaluation = CustomerSupportOutcomeEvaluationRecord(
            user_id=user_id,
            support_outcome_id=outcome.id,
            review_plan_id=(outcome.review_plan_id),
            workflow_run_id=(outcome.workflow_run_id),
            evaluation_version=1,
            result=result,
            reason_code=(f"{result}_reason"),
            summary=(f"Objective is {result}."),
            confidence=0.9,
            retryable=(
                result
                not in {
                    "achieved",
                    "intentionally_not_executed",
                }
            ),
            achieved_operation_count=(achieved),
            failed_operation_count=failed,
            pending_operation_count=pending,
            unknown_operation_count=unknown,
            not_executed_operation_count=(not_executed),
            observed_outcome_json={},
            evidence_json=[],
        )
        db.add(evaluation)
        await db.flush()

        event = await PlatformEventStore(db).append(
            user_id=user_id,
            event_type=(SUPPORT_OUTCOME_EVALUATED_EVENT),
            source="test",
            payload={
                "evaluation_id": str(evaluation.id),
                "support_outcome_id": str(outcome.id),
                "evaluation_version": 1,
                "result": result,
            },
            meta={
                "workflow_run_id": str(outcome.workflow_run_id),
            },
            commit=False,
        )

        await db.commit()

        return (
            outcome.id,
            evaluation.id,
            event.id,
        )


def test_event_and_job_handlers_registered():
    handlers = build_default_event_registry().handlers_for(
        SUPPORT_OUTCOME_EVALUATED_EVENT
    )

    assert enqueue_customer_support_objective_resolution in handlers

    assert (
        build_default_job_registry().get(CUSTOMER_SUPPORT_OBJECTIVE_RESOLUTION_JOB)
        is project_customer_support_objective_resolution_job
    )


@pytest.mark.asyncio
async def test_duplicate_event_delivery_reuses_job():
    user_id = uuid4()
    outcome_id, evaluation_id, event_id = await _create_source(
        user_id=user_id,
        statuses=["completed"],
        result="achieved",
    )

    async with SessionLocal() as db:
        event = await PlatformEventStore(db).get(event_id)

        first = await enqueue_customer_support_objective_resolution(
            event,
            SimpleNamespace(db=db),
        )
        second = await enqueue_customer_support_objective_resolution(
            event,
            SimpleNamespace(db=db),
        )

        await db.commit()

    assert first["job_id"] == second["job_id"]

    async with SessionLocal() as db:
        jobs = list(
            (
                await db.execute(
                    select(PlatformJob).where(
                        PlatformJob.job_type
                        == (CUSTOMER_SUPPORT_OBJECTIVE_RESOLUTION_JOB),
                        PlatformJob.user_id == user_id,
                    )
                )
            )
            .scalars()
            .all()
        )

    assert len(jobs) == 1
    assert jobs[0].payload["evaluation_id"] == str(evaluation_id)
    assert jobs[0].payload["support_outcome_id"] == str(outcome_id)


@pytest.mark.asyncio
async def test_job_projects_one_durable_resolution():
    user_id = uuid4()
    outcome_id, evaluation_id, event_id = await _create_source(
        user_id=user_id,
        statuses=[
            "completed",
            "submitted",
        ],
        result="partially_achieved",
    )

    async with SessionLocal() as db:
        event = await PlatformEventStore(db).get(event_id)

        scheduled = await enqueue_customer_support_objective_resolution(
            event,
            SimpleNamespace(db=db),
        )
        await db.commit()

        job = await db.get(
            PlatformJob,
            UUID(scheduled["job_id"]),
        )

        result = await project_customer_support_objective_resolution_job(
            job.payload,
            SimpleNamespace(
                db=db,
                job=job,
            ),
        )

        duplicate = await project_customer_support_objective_resolution_job(
            job.payload,
            SimpleNamespace(
                db=db,
                job=job,
            ),
        )

    assert result["created"] is True
    assert duplicate["created"] is False
    assert result["resolution_record_id"] == duplicate["resolution_record_id"]
    assert result["resolution_status"] == ("partially_achieved")
    assert result["is_terminal"] is False

    async with SessionLocal() as db:
        resolutions = list(
            (
                await db.execute(
                    select(ObjectiveResolutionRecord).where(
                        ObjectiveResolutionRecord.user_id == user_id
                    )
                )
            )
            .scalars()
            .all()
        )

        events = list(
            (
                await db.execute(
                    select(PlatformEvent).where(
                        PlatformEvent.user_id == user_id,
                        PlatformEvent.event_type
                        == (OBJECTIVE_RESOLUTION_ASSESSED_EVENT),
                    )
                )
            )
            .scalars()
            .all()
        )

    assert len(resolutions) == 1
    assert len(events) == 1

    resolution = resolutions[0]

    assert resolution.source_outcome_ref == str(outcome_id)
    assert resolution.source_evaluation_ref == str(evaluation_id)
    assert resolution.operation_count == 2
    assert resolution.achieved_operation_count == 1
    assert resolution.pending_operation_count == 1
    assert resolution.unresolved_operation_count == 1


@pytest.mark.asyncio
async def test_job_rejects_owner_mismatch():
    owner_id = uuid4()
    other_id = uuid4()

    _, _, event_id = await _create_source(
        user_id=owner_id,
        statuses=["completed"],
        result="achieved",
    )

    async with SessionLocal() as db:
        event = await PlatformEventStore(db).get(event_id)

        scheduled = await enqueue_customer_support_objective_resolution(
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
            await project_customer_support_objective_resolution_job(
                job.payload,
                SimpleNamespace(
                    db=db,
                    job=job,
                ),
            )
