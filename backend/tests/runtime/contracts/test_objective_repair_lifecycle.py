from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.platform.jobs.service import JobService
from app.runtime.objectives.repair import (
    OBJECTIVE_REPAIR_EXECUTION_STATUS_COMPLETED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_FAILED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_REJECTED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_RUNNING,
    ObjectiveRepairExecutionConflictError,
    ObjectiveRepairExecutionService,
    ObjectiveRepairExecutionTransitionError,
)
from tests.runtime.contracts.test_objective_repair_persistence import (
    _plan,
    _request,
    _resolution_record,
    _source_event,
)


async def _workflow_job(
    db,
    *,
    user_id,
):
    return await JobService(db).enqueue(
        user_id=user_id,
        job_type="workflow.run",
        payload={
            "workflow": {
                "name": "Repair fixture",
                "version": "1.0.0",
                "nodes": [],
                "edges": [],
            },
            "message": "Repair lifecycle fixture",
            "extras": {
                "objective_repair_test": True,
            },
        },
        idempotency_key=(f"objective-repair-lifecycle-test:{uuid4()}"),
    )


async def _record_plan(
    db,
    *,
    user_id,
):
    resolution_source = await _source_event(
        db,
        user_id=user_id,
        suffix=str(uuid4()),
    )
    resolution = await _resolution_record(
        db,
        user_id=user_id,
        source_event_id=resolution_source.id,
    )
    repair_source = await _source_event(
        db,
        user_id=user_id,
        suffix=str(uuid4()),
    )

    return await ObjectiveRepairExecutionService(db).record_plan(
        source_event_id=repair_source.id,
        user_id=user_id,
        tenant_id="tenant-1",
        resolution_record_id=resolution.id,
        request=_request(),
        plan=_plan(),
        planner_ref=("customer_support_objective_repair"),
        planner_policy_version=1,
    )


@pytest.mark.asyncio
async def test_repair_execution_full_lifecycle():
    user_id = uuid4()
    run_id = str(uuid4())

    workflow = {
        "name": "Repair workflow",
        "version": "1.0.0",
        "nodes": [],
        "edges": [],
    }

    async with SessionLocal() as db:
        write = await _record_plan(
            db,
            user_id=user_id,
        )
        service = ObjectiveRepairExecutionService(db)
        job = await _workflow_job(
            db,
            user_id=user_id,
        )

        queued = await service.queue_workflow(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_json=workflow,
            workflow_job_id=job.id,
        )

        assert queued.status == (OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED)
        assert queued.workflow_job_id == job.id
        assert queued.workflow_json == workflow

        running = await service.mark_running(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_run_id=run_id,
        )

        assert running.status == (OBJECTIVE_REPAIR_EXECUTION_STATUS_RUNNING)
        assert running.workflow_run_id == run_id
        assert running.launched_at is not None

        paused = await service.mark_paused(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_run_id=run_id,
            result_json={
                "status": "paused",
                "wait": {
                    "kind": "human_approval",
                },
            },
        )

        assert paused.status == (OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED)
        assert paused.completed_at is None

        resumed = await service.mark_running(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_run_id=run_id,
        )

        assert resumed.status == (OBJECTIVE_REPAIR_EXECUTION_STATUS_RUNNING)

        completed = await service.mark_completed(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_run_id=run_id,
            result_json={
                "status": ("provider_operations_completed"),
            },
        )

        assert completed.status == (OBJECTIVE_REPAIR_EXECUTION_STATUS_COMPLETED)
        assert completed.result_json == {
            "status": ("provider_operations_completed"),
        }
        assert completed.completed_at is not None
        assert completed.failure_code is None
        assert completed.failure_message is None


@pytest.mark.asyncio
async def test_rejected_is_terminal_without_failure():
    user_id = uuid4()
    run_id = str(uuid4())

    async with SessionLocal() as db:
        write = await _record_plan(
            db,
            user_id=user_id,
        )
        service = ObjectiveRepairExecutionService(db)
        job = await _workflow_job(
            db,
            user_id=user_id,
        )

        await service.queue_workflow(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_json={
                "name": "Repair",
                "nodes": [],
                "edges": [],
            },
            workflow_job_id=job.id,
        )
        await service.mark_running(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_run_id=run_id,
        )

        record = await service.mark_rejected(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_run_id=run_id,
            result_json={
                "status": "rejected",
                "approval_granted": False,
            },
        )

        assert record.status == (OBJECTIVE_REPAIR_EXECUTION_STATUS_REJECTED)
        assert record.failure_code is None
        assert record.failure_message is None
        assert record.completed_at is not None


@pytest.mark.asyncio
async def test_failed_records_durable_failure():
    user_id = uuid4()

    async with SessionLocal() as db:
        write = await _record_plan(
            db,
            user_id=user_id,
        )
        service = ObjectiveRepairExecutionService(db)
        job = await _workflow_job(
            db,
            user_id=user_id,
        )

        await service.queue_workflow(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_json={
                "name": "Repair",
                "nodes": [],
                "edges": [],
            },
            workflow_job_id=job.id,
        )

        record = await service.mark_failed(
            user_id=user_id,
            repair_execution_id=write.record.id,
            failure_code="workflow_job_failed",
            failure_message="Workflow job failed.",
            result_json={
                "status": "error",
            },
        )

        assert record.status == (OBJECTIVE_REPAIR_EXECUTION_STATUS_FAILED)
        assert record.failure_code == ("workflow_job_failed")
        assert record.failure_message == ("Workflow job failed.")
        assert record.result_json == {
            "status": "error",
        }
        assert record.completed_at is not None


@pytest.mark.asyncio
async def test_queue_is_idempotent_for_same_facts():
    user_id = uuid4()
    workflow = {
        "name": "Repair",
        "nodes": [],
        "edges": [],
    }

    async with SessionLocal() as db:
        write = await _record_plan(
            db,
            user_id=user_id,
        )
        service = ObjectiveRepairExecutionService(db)
        job = await _workflow_job(
            db,
            user_id=user_id,
        )

        first = await service.queue_workflow(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_json=workflow,
            workflow_job_id=job.id,
        )
        second = await service.queue_workflow(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_json=workflow,
            workflow_job_id=job.id,
        )

        assert first.id == second.id
        assert second.status == (OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED)


@pytest.mark.asyncio
async def test_queue_conflict_is_rejected():
    user_id = uuid4()

    async with SessionLocal() as db:
        write = await _record_plan(
            db,
            user_id=user_id,
        )
        service = ObjectiveRepairExecutionService(db)
        first_job = await _workflow_job(
            db,
            user_id=user_id,
        )
        second_job = await _workflow_job(
            db,
            user_id=user_id,
        )

        await service.queue_workflow(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_json={
                "name": "Repair A",
                "nodes": [],
                "edges": [],
            },
            workflow_job_id=first_job.id,
        )

        with pytest.raises(
            ObjectiveRepairExecutionConflictError,
            match="different workflow facts",
        ):
            await service.queue_workflow(
                user_id=user_id,
                repair_execution_id=write.record.id,
                workflow_json={
                    "name": "Repair B",
                    "nodes": [],
                    "edges": [],
                },
                workflow_job_id=second_job.id,
            )


@pytest.mark.asyncio
async def test_invalid_transition_is_rejected():
    user_id = uuid4()

    async with SessionLocal() as db:
        write = await _record_plan(
            db,
            user_id=user_id,
        )

        with pytest.raises(
            ObjectiveRepairExecutionTransitionError,
            match="planned -> completed",
        ):
            await ObjectiveRepairExecutionService(db).mark_completed(
                user_id=user_id,
                repair_execution_id=(write.record.id),
                workflow_run_id=str(uuid4()),
                result_json={
                    "status": "completed",
                },
            )


@pytest.mark.asyncio
async def test_terminal_write_is_idempotent():
    user_id = uuid4()
    run_id = str(uuid4())
    result = {
        "status": "provider_operations_completed",
    }

    async with SessionLocal() as db:
        write = await _record_plan(
            db,
            user_id=user_id,
        )
        service = ObjectiveRepairExecutionService(db)
        job = await _workflow_job(
            db,
            user_id=user_id,
        )

        await service.queue_workflow(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_json={
                "name": "Repair",
                "nodes": [],
                "edges": [],
            },
            workflow_job_id=job.id,
        )
        await service.mark_running(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_run_id=run_id,
        )

        first = await service.mark_completed(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_run_id=run_id,
            result_json=result,
        )
        second = await service.mark_completed(
            user_id=user_id,
            repair_execution_id=write.record.id,
            workflow_run_id=run_id,
            result_json=result,
        )

        assert first.id == second.id
        assert second.status == (OBJECTIVE_REPAIR_EXECUTION_STATUS_COMPLETED)
