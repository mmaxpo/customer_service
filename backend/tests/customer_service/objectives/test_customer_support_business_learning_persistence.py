from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.models.outcomes import (
    CustomerSupportOutcomeEvaluationRecord,
    CustomerSupportOutcomeRecord,
)
from app.domains.customer_service.services.support.learning.customer_support_business_learning_projection import (
    SUPPORT_OUTCOME_EVALUATED_EVENT,
    CustomerSupportBusinessLearningProjector,
)
from app.models.models import (
    BusinessLearningObservationRecord,
    PlatformEvent,
)
from app.platform.composition import (
    build_default_event_registry,
    build_default_job_registry,
)


async def _create_sources(
    *,
    user_id,
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
            status="mixed",
            operation_count=2,
            customer_message="Refund submitted.",
            operations_json=[
                {
                    "operation_type": "refund",
                    "status": "completed",
                },
                {
                    "operation_type": "email",
                    "status": "submitted",
                },
            ],
            outcome_json={
                "decision": "approved",
                "status": "mixed",
            },
        )
        db.add(outcome)
        await db.flush()

        evaluation = CustomerSupportOutcomeEvaluationRecord(
            user_id=user_id,
            support_outcome_id=outcome.id,
            review_plan_id=(outcome.review_plan_id),
            workflow_run_id=(outcome.workflow_run_id),
            evaluation_version=1,
            result="partially_achieved",
            reason_code=("completed_and_incomplete_operations"),
            summary=("Some operations completed."),
            confidence=0.9,
            retryable=False,
            achieved_operation_count=1,
            failed_operation_count=0,
            pending_operation_count=1,
            unknown_operation_count=0,
            not_executed_operation_count=0,
            observed_outcome_json={
                "decision": "approved",
                "status": "mixed",
            },
            evidence_json=[
                {
                    "kind": ("canonical_support_outcome"),
                    "source": ("customer_service.support_outcome"),
                    "data": {
                        "not_persisted": True,
                    },
                },
            ],
        )
        db.add(evaluation)
        await db.flush()

        event = PlatformEvent(
            user_id=user_id,
            event_type=(SUPPORT_OUTCOME_EVALUATED_EVENT),
            source=("customer_service.support_outcome_evaluation"),
            payload={
                "evaluation_id": str(evaluation.id),
                "support_outcome_id": str(outcome.id),
                "evaluation_version": 1,
                "result": evaluation.result,
            },
            meta={
                "workflow_run_id": str(outcome.workflow_run_id),
                "conversation_id": str(outcome.conversation_id),
            },
            status="published",
        )
        db.add(event)

        await db.commit()
        await db.refresh(outcome)
        await db.refresh(evaluation)
        await db.refresh(event)

        return outcome, evaluation, event


@pytest.mark.asyncio
async def test_projector_persists_business_observation():
    user_id = uuid4()

    outcome, evaluation, event = await _create_sources(user_id=user_id)

    async with SessionLocal() as db:
        result = await CustomerSupportBusinessLearningProjector(db).project_event(event)

        assert result["inserted"] is True
        assert result["result"] == "partially_achieved"
        assert result["is_final"] is True

    async with SessionLocal() as db:
        row = await db.scalar(
            select(BusinessLearningObservationRecord).where(
                BusinessLearningObservationRecord.source_evaluation_record_id
                == evaluation.id
            )
        )

        assert row is not None
        assert row.user_id == user_id
        assert row.source_outcome_record_id == outcome.id
        assert row.objective_namespace == "customer_service.support"
        assert row.achieved_operation_count == 1
        assert row.pending_operation_count == 1
        assert row.is_final is True

        assert row.evidence_summary_json == {
            "count": 1,
            "items": [
                {
                    "kind": ("canonical_support_outcome"),
                    "source": ("customer_service.support_outcome"),
                },
            ],
        }

        assert "data" not in row.evidence_summary_json["items"][0]


@pytest.mark.asyncio
async def test_projector_is_idempotent():
    user_id = uuid4()

    _, evaluation, event = await _create_sources(user_id=user_id)

    async with SessionLocal() as db:
        projector = CustomerSupportBusinessLearningProjector(db)

        first = await projector.project_event(event)
        second = await projector.project_event(event)

        assert first["inserted"] is True
        assert second["inserted"] is False
        assert (
            first["business_learning_observation_id"]
            == second["business_learning_observation_id"]
        )

    async with SessionLocal() as db:
        rows = list(
            (
                await db.execute(
                    select(BusinessLearningObservationRecord).where(
                        BusinessLearningObservationRecord.source_evaluation_record_id
                        == evaluation.id
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(rows) == 1


@pytest.mark.asyncio
async def test_projector_rejects_cross_user_event():
    owner_id = uuid4()
    other_id = uuid4()

    _, _, event = await _create_sources(user_id=owner_id)
    event.user_id = other_id

    async with SessionLocal() as db:
        with pytest.raises(
            ValueError,
            match=("evaluation was not found"),
        ):
            await CustomerSupportBusinessLearningProjector(db).project_event(event)


@pytest.mark.asyncio
async def test_projector_rejects_wrong_event_type():
    user_id = uuid4()

    _, _, event = await _create_sources(user_id=user_id)
    event.event_type = "wrong.event"

    async with SessionLocal() as db:
        with pytest.raises(
            ValueError,
            match="Unexpected",
        ):
            await CustomerSupportBusinessLearningProjector(db).project_event(event)


def test_business_learning_event_handler_is_registered():
    from app.domains.customer_service.events.handlers import (
        enqueue_customer_support_business_learning,
    )

    handlers = build_default_event_registry().handlers_for(
        SUPPORT_OUTCOME_EVALUATED_EVENT
    )

    assert enqueue_customer_support_business_learning in handlers


def test_business_learning_job_handler_is_registered():
    from app.domains.customer_service.jobs.handlers import (
        CUSTOMER_SUPPORT_BUSINESS_LEARNING_JOB,
        project_customer_support_business_learning_job,
    )

    assert build_default_job_registry().get(CUSTOMER_SUPPORT_BUSINESS_LEARNING_JOB) is (
        project_customer_support_business_learning_job
    )


@pytest.mark.asyncio
async def test_duplicate_evaluated_event_enqueues_one_business_learning_job():
    from types import SimpleNamespace

    from app.domains.customer_service.events.handlers import (
        CUSTOMER_SUPPORT_BUSINESS_LEARNING_JOB,
        enqueue_customer_support_business_learning,
    )
    from app.models.models import PlatformJob

    user_id = uuid4()
    _, evaluation, event = await _create_sources(user_id=user_id)

    async with SessionLocal() as db:
        persisted_event = await db.get(
            PlatformEvent,
            event.id,
        )

        ctx = SimpleNamespace(
            db=db,
            event=persisted_event,
        )

        first = await enqueue_customer_support_business_learning(
            persisted_event,
            ctx,
        )
        second = await enqueue_customer_support_business_learning(
            persisted_event,
            ctx,
        )

        assert first["scheduled"] is True
        assert second["scheduled"] is True
        assert first["job_id"] == second["job_id"]

        rows = list(
            (
                await db.execute(
                    select(PlatformJob).where(
                        PlatformJob.job_type
                        == (CUSTOMER_SUPPORT_BUSINESS_LEARNING_JOB),
                        PlatformJob.idempotency_key
                        == (f"customer-support-business-learning:{evaluation.id}"),
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(rows) == 1


@pytest.mark.asyncio
async def test_business_learning_job_persists_observation():
    from types import SimpleNamespace

    from app.domains.customer_service.events.handlers import (
        enqueue_customer_support_business_learning,
    )
    from app.domains.customer_service.jobs.handlers import (
        project_customer_support_business_learning_job,
    )
    from app.models.models import PlatformJob

    user_id = uuid4()
    outcome, evaluation, event = await _create_sources(user_id=user_id)

    async with SessionLocal() as db:
        persisted_event = await db.get(
            PlatformEvent,
            event.id,
        )

        scheduled = await enqueue_customer_support_business_learning(
            persisted_event,
            SimpleNamespace(
                db=db,
                event=persisted_event,
            ),
        )

        job = await db.get(
            PlatformJob,
            UUID(scheduled["job_id"]),
        )

        result = await project_customer_support_business_learning_job(
            job.payload,
            SimpleNamespace(
                db=db,
                job=job,
                worker_id="test-worker",
            ),
        )

        assert result["inserted"] is True
        assert result["result"] == "partially_achieved"

    async with SessionLocal() as db:
        row = await db.scalar(
            select(BusinessLearningObservationRecord).where(
                BusinessLearningObservationRecord.source_evaluation_record_id
                == evaluation.id
            )
        )

        assert row is not None
        assert row.source_outcome_record_id == outcome.id


@pytest.mark.asyncio
async def test_business_learning_job_rejects_cross_user_event():
    from types import SimpleNamespace

    from app.domains.customer_service.jobs.handlers import (
        project_customer_support_business_learning_job,
    )

    owner_id = uuid4()
    other_id = uuid4()

    _, evaluation, event = await _create_sources(user_id=owner_id)

    fake_job = SimpleNamespace(
        user_id=other_id,
    )

    async with SessionLocal() as db:
        with pytest.raises(
            ValueError,
            match="ownership",
        ):
            await project_customer_support_business_learning_job(
                {
                    "source_event_id": str(event.id),
                    "evaluation_id": str(evaluation.id),
                    "support_outcome_id": str(evaluation.support_outcome_id),
                },
                SimpleNamespace(
                    db=db,
                    job=fake_job,
                    worker_id="test-worker",
                ),
            )
