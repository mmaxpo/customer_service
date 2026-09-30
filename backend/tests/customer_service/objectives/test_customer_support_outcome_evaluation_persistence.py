from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.events.handlers import (
    enqueue_customer_support_outcome_evaluation,
)
from app.domains.customer_service.jobs.handlers import (
    CUSTOMER_SUPPORT_OUTCOME_EVALUATION_JOB,
    evaluate_customer_support_outcome_job,
)
from app.domains.customer_service.models.outcomes import (
    CustomerSupportOutcomeEvaluationRecord,
    CustomerSupportOutcomeRecord,
)
from app.domains.customer_service.services.support.outcome.customer_support_outcome_evaluation_service import (
    SUPPORT_OUTCOME_EVALUATED_EVENT,
    CustomerSupportOutcomeEvaluationService,
)
from app.models.models import (
    PlatformEvent,
    PlatformJob,
)
from app.platform.composition import (
    build_default_event_registry,
    build_default_job_registry,
)
from app.platform.jobs.worker import JobWorker


async def _create_outcome(
    *,
    user_id: UUID,
    statuses: list[str],
    decision: str = "approved",
) -> CustomerSupportOutcomeRecord:
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
            decision=decision,
            status=(statuses[0] if statuses and len(set(statuses)) == 1 else "mixed"),
            operation_count=len(statuses),
            customer_message="Outcome recorded.",
            operations_json=[
                {
                    "operation_type": ("whole_refund"),
                    "status": status,
                }
                for status in statuses
            ],
            outcome_json={
                "decision": decision,
                "operations": statuses,
            },
        )
        db.add(outcome)
        await db.commit()
        await db.refresh(outcome)
        return outcome


@pytest.mark.asyncio
async def test_evaluation_service_is_idempotent():
    user_id = uuid4()
    outcome = await _create_outcome(
        user_id=user_id,
        statuses=["completed"],
    )

    async with SessionLocal() as db:
        service = CustomerSupportOutcomeEvaluationService(db)

        first = await service.evaluate(
            user_id=user_id,
            support_outcome_id=outcome.id,
        )
        second = await service.evaluate(
            user_id=user_id,
            support_outcome_id=outcome.id,
        )

    assert first.created is True
    assert second.created is False
    assert first.record.id == second.record.id
    assert first.event_id is not None
    assert second.event_id is None
    assert first.record.result == "achieved"

    async with SessionLocal() as db:
        evaluations = list(
            (
                await db.execute(
                    select(CustomerSupportOutcomeEvaluationRecord).where(
                        CustomerSupportOutcomeEvaluationRecord.user_id == user_id,
                        CustomerSupportOutcomeEvaluationRecord.support_outcome_id
                        == outcome.id,
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
                        PlatformEvent.event_type == SUPPORT_OUTCOME_EVALUATED_EVENT,
                    )
                )
            )
            .scalars()
            .all()
        )

    assert len(evaluations) == 1
    assert len(events) == 1


@pytest.mark.asyncio
async def test_evaluation_is_user_scoped():
    owner_id = uuid4()
    other_user_id = uuid4()

    outcome = await _create_outcome(
        user_id=owner_id,
        statuses=["completed"],
    )

    async with SessionLocal() as db:
        with pytest.raises(
            ValueError,
            match="not found for user",
        ):
            await CustomerSupportOutcomeEvaluationService(db).evaluate(
                user_id=other_user_id,
                support_outcome_id=outcome.id,
            )


def test_event_and_job_handlers_are_registered():
    assert (
        enqueue_customer_support_outcome_evaluation
        in build_default_event_registry().handlers_for(
            "customer_service.support.outcome.recorded"
        )
    )

    assert (
        build_default_job_registry().get(CUSTOMER_SUPPORT_OUTCOME_EVALUATION_JOB)
        is evaluate_customer_support_outcome_job
    )


@pytest.mark.asyncio
async def test_event_to_job_to_evaluation_flow():
    user_id = uuid4()
    outcome = await _create_outcome(
        user_id=user_id,
        statuses=["prepared"],
    )

    async with SessionLocal() as db:
        event = PlatformEvent(
            user_id=user_id,
            event_type=("customer_service.support.outcome.recorded"),
            source=("customer_service.support_outcome"),
            payload={
                "outcome_id": str(outcome.id),
                "review_plan_id": (outcome.review_plan_id),
            },
            meta={
                "workflow_run_id": str(outcome.workflow_run_id),
            },
            status="published",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        first = await enqueue_customer_support_outcome_evaluation(
            event,
            SimpleNamespace(
                db=db,
                event=event,
            ),
        )

        second = await enqueue_customer_support_outcome_evaluation(
            event,
            SimpleNamespace(
                db=db,
                event=event,
            ),
        )

        await db.commit()

        assert first["job_id"] == second["job_id"]

        jobs = list(
            (
                await db.execute(
                    select(PlatformJob).where(
                        PlatformJob.job_type
                        == (CUSTOMER_SUPPORT_OUTCOME_EVALUATION_JOB),
                        PlatformJob.idempotency_key
                        == (f"customer-support-outcome-evaluation:{outcome.id}:v1"),
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(jobs) == 1
        job_id = jobs[0].id

    async with SessionLocal() as db:
        completed_job = await JobWorker(
            db,
            worker_id=("support-outcome-evaluation-test"),
        ).run_once(job_id=job_id)

        assert completed_job is not None
        assert completed_job.status == "succeeded"
        assert completed_job.result["result"] == "progressing"
        assert completed_job.result["created"] is True

    async with SessionLocal() as db:
        evaluation = await db.scalar(
            select(CustomerSupportOutcomeEvaluationRecord).where(
                CustomerSupportOutcomeEvaluationRecord.support_outcome_id == outcome.id
            )
        )

        assert evaluation is not None
        assert evaluation.result == "progressing"
        assert evaluation.pending_operation_count == 1


@pytest.mark.asyncio
async def test_job_rejects_ownership_mismatch():
    owner_id = uuid4()
    other_user_id = uuid4()

    outcome = await _create_outcome(
        user_id=owner_id,
        statuses=["completed"],
    )

    async with SessionLocal() as db:
        event = PlatformEvent(
            user_id=owner_id,
            event_type=("customer_service.support.outcome.recorded"),
            source=("customer_service.support_outcome"),
            payload={
                "outcome_id": str(outcome.id),
            },
            meta={},
            status="published",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        ctx = SimpleNamespace(
            db=db,
            job=SimpleNamespace(
                user_id=other_user_id,
            ),
        )

        with pytest.raises(
            ValueError,
            match="ownership does not match",
        ):
            await evaluate_customer_support_outcome_job(
                {
                    "source_event_id": str(event.id),
                    "support_outcome_id": str(outcome.id),
                    "evaluation_version": 1,
                },
                ctx,
            )
