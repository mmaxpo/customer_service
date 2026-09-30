from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.domains.customer_service.jobs.handlers import (
    CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB,
    launch_customer_support_objective_repair_job,
    register_customer_service_job_handlers,
)
from app.domains.customer_service.services.support.repair.launch import (
    CustomerSupportRepairLaunchCoordinator,
    CustomerSupportRepairLaunchError,
)
from app.runtime.objectives.repair import (
    OBJECTIVE_REPAIR_EXECUTION_STATUS_PLANNED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED,
    ObjectiveRepairAction,
    ObjectiveRepairDisposition,
    ObjectiveRepairPlan,
)
from app.runtime.objectives.resolution import (
    ObjectiveReference,
)


def _plan(
    disposition=(ObjectiveRepairDisposition.WAIT_FOR_RESULT),
):
    objective = ObjectiveReference(
        namespace="customer_service.support",
        objective_type="partial_refund",
        objective_ref="review-1",
        objective_version=1,
    )

    action_kwargs = {
        "action_ref": "repair-action-1",
        "disposition": disposition,
        "target_operation_refs": ("support_operation:001:partial_refund:line-1",),
        "reason_code": "operation_unresolved",
        "summary": "Repair unresolved operation.",
        "human_approval_required": (
            disposition
            in {
                ObjectiveRepairDisposition.REQUEST_HUMAN_ACTION,
                ObjectiveRepairDisposition.REPLAN_REMAINING,
            }
        ),
        "automatic_execution_allowed": False,
        "confidence": 0.95,
    }

    if disposition == ObjectiveRepairDisposition.WAIT_FOR_RESULT:
        action_kwargs["wait_for_event_type"] = (
            "customer_service.support.operation.status_changed"
        )

    action = ObjectiveRepairAction(
        **action_kwargs,
    )

    return ObjectiveRepairPlan(
        objective=objective,
        repair_request_ref="repair-request-1",
        disposition=disposition,
        reason_code="operation_unresolved",
        summary="Repair the unresolved support operation.",
        confidence=0.95,
        actions=(action,),
        planned_target_refs=("support_operation:001:partial_refund:line-1",),
        deferred_target_refs=(),
        unhandled_target_refs=(),
        human_approval_required=(action.human_approval_required),
        automatic_execution_allowed=False,
    )


def _record(plan):
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        tenant_id="tenant-1",
        resolution_record_id=uuid4(),
        objective_namespace=(plan.objective.namespace),
        objective_type=(plan.objective.objective_type),
        objective_ref=plan.objective.objective_ref,
        objective_version=(plan.objective.objective_version),
        repair_request_ref=(plan.repair_request_ref),
        controlling_disposition=(plan.disposition.value),
        status=(OBJECTIVE_REPAIR_EXECUTION_STATUS_PLANNED),
        plan_json=plan.model_dump(mode="json"),
        attempt_number=1,
        workflow_json=None,
        workflow_job_id=None,
    )


def _workflow(kind="non_mutating"):
    return {
        "name": "Repair workflow",
        "version": "1.0.0",
        "nodes": [
            {
                "id": "trigger",
                "type": "custom",
                "data": {
                    "nodeType": "trigger.message",
                },
            },
            {
                "id": "response",
                "type": "custom",
                "data": {
                    "nodeType": "response",
                    "answer": "done",
                },
            },
        ],
        "edges": [
            {
                "source": "trigger",
                "target": "response",
            },
        ],
        "metadata": {
            "kind": kind,
        },
    }


@pytest.mark.asyncio
async def test_launches_non_mutating_workflow_atomically():
    plan = _plan()
    record = _record(plan)
    workflow = _workflow()

    repair_repository = SimpleNamespace(
        get_by_id_for_user=AsyncMock(return_value=record)
    )

    lifecycle = SimpleNamespace(
        queue_workflow=AsyncMock(
            return_value=SimpleNamespace(
                **{
                    **record.__dict__,
                    "status": (OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED),
                }
            )
        )
    )

    workflow_job = SimpleNamespace(
        id=uuid4(),
        user_id=record.user_id,
        job_type="workflow.run",
    )

    jobs = SimpleNamespace(enqueue=AsyncMock(return_value=workflow_job))

    workflow_builder = SimpleNamespace(
        build_non_mutating=Mock(return_value=workflow),
        build_replanned_operations=Mock(),
        objective_repair_extras=Mock(
            return_value={
                "repair_execution_id": str(record.id),
            }
        ),
        workflow_job_idempotency_key=Mock(
            return_value=(f"customer-support-repair-workflow:{record.id}:workflow-v1")
        ),
    )

    db = SimpleNamespace(
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )

    coordinator = CustomerSupportRepairLaunchCoordinator(
        db,
        repairs=repair_repository,
        lifecycle=lifecycle,
        workflow_builder=workflow_builder,
        jobs=jobs,
        job_repository=SimpleNamespace(),
    )

    result = await coordinator.launch(
        user_id=record.user_id,
        repair_execution_id=record.id,
    )

    assert result.already_queued is False
    assert result.workflow == workflow

    workflow_builder.build_non_mutating.assert_called_once()
    workflow_builder.build_replanned_operations.assert_not_called()

    jobs.enqueue.assert_awaited_once()
    enqueue_kwargs = jobs.enqueue.await_args.kwargs

    assert enqueue_kwargs["commit"] is False
    assert enqueue_kwargs["job_type"] == "workflow.run"
    assert enqueue_kwargs["user_id"] == record.user_id
    assert enqueue_kwargs["max_attempts"] == 5

    lifecycle.queue_workflow.assert_awaited_once_with(
        user_id=record.user_id,
        repair_execution_id=record.id,
        workflow_json=workflow,
        workflow_job_id=workflow_job.id,
        commit=False,
    )

    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_replanned_launch_loads_canonical_plan():
    plan = _plan(ObjectiveRepairDisposition.REPLAN_REMAINING)
    record = _record(plan)
    workflow = _workflow("replanned_provider_operations")

    source_review_plan = SimpleNamespace()
    repair_review_plan = SimpleNamespace()

    loader = SimpleNamespace(
        load_for_resolution=AsyncMock(
            return_value=SimpleNamespace(review_plan=source_review_plan)
        )
    )

    repair_review_builder = SimpleNamespace(build=Mock(return_value=repair_review_plan))

    workflow_builder = SimpleNamespace(
        build_non_mutating=Mock(),
        build_replanned_operations=Mock(return_value=workflow),
        objective_repair_extras=Mock(return_value={}),
        workflow_job_idempotency_key=Mock(return_value="repair-key"),
    )

    workflow_job = SimpleNamespace(
        id=uuid4(),
        user_id=record.user_id,
        job_type="workflow.run",
    )

    coordinator = CustomerSupportRepairLaunchCoordinator(
        SimpleNamespace(
            commit=AsyncMock(),
            refresh=AsyncMock(),
        ),
        repairs=SimpleNamespace(get_by_id_for_user=AsyncMock(return_value=record)),
        lifecycle=SimpleNamespace(
            queue_workflow=AsyncMock(
                return_value=SimpleNamespace(
                    **{
                        **record.__dict__,
                        "status": (OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED),
                    }
                )
            )
        ),
        review_plan_loader=loader,
        repair_review_builder=(repair_review_builder),
        workflow_builder=workflow_builder,
        jobs=SimpleNamespace(enqueue=AsyncMock(return_value=workflow_job)),
        job_repository=SimpleNamespace(),
    )

    await coordinator.launch(
        user_id=record.user_id,
        repair_execution_id=record.id,
    )

    loader.load_for_resolution.assert_awaited_once_with(
        user_id=record.user_id,
        resolution_record_id=(record.resolution_record_id),
    )

    repair_review_builder.build.assert_called_once_with(
        source_review_plan=source_review_plan,
        repair_plan=plan,
    )

    workflow_builder.build_replanned_operations.assert_called_once()
    workflow_builder.build_non_mutating.assert_not_called()


@pytest.mark.asyncio
async def test_queued_launch_is_idempotent():
    plan = _plan()
    record = _record(plan)
    workflow_job_id = uuid4()
    workflow = _workflow()

    record.status = OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED
    record.workflow_job_id = workflow_job_id
    record.workflow_json = workflow

    workflow_job = SimpleNamespace(
        id=workflow_job_id,
        user_id=record.user_id,
        job_type="workflow.run",
    )

    jobs = SimpleNamespace(enqueue=AsyncMock())
    lifecycle = SimpleNamespace(queue_workflow=AsyncMock())

    coordinator = CustomerSupportRepairLaunchCoordinator(
        SimpleNamespace(),
        repairs=SimpleNamespace(get_by_id_for_user=AsyncMock(return_value=record)),
        lifecycle=lifecycle,
        jobs=jobs,
        job_repository=SimpleNamespace(get=AsyncMock(return_value=workflow_job)),
    )

    result = await coordinator.launch(
        user_id=record.user_id,
        repair_execution_id=record.id,
    )

    assert result.already_queued is True
    assert result.workflow_job.id == workflow_job_id

    jobs.enqueue.assert_not_awaited()
    lifecycle.queue_workflow.assert_not_awaited()


@pytest.mark.asyncio
async def test_plan_metadata_conflict_is_rejected():
    plan = _plan()
    record = _record(plan)
    record.controlling_disposition = ObjectiveRepairDisposition.STOP_REPAIR.value

    coordinator = CustomerSupportRepairLaunchCoordinator(
        SimpleNamespace(),
        repairs=SimpleNamespace(get_by_id_for_user=AsyncMock(return_value=record)),
    )

    with pytest.raises(
        CustomerSupportRepairLaunchError,
        match="disposition",
    ):
        await coordinator.launch(
            user_id=record.user_id,
            repair_execution_id=record.id,
        )


@pytest.mark.asyncio
async def test_invalid_generated_workflow_is_rejected():
    plan = _plan()
    record = _record(plan)

    workflow_builder = SimpleNamespace(
        build_non_mutating=Mock(
            return_value={
                "name": "invalid",
                "nodes": [],
                "edges": [],
            }
        ),
    )

    jobs = SimpleNamespace(enqueue=AsyncMock())

    coordinator = CustomerSupportRepairLaunchCoordinator(
        SimpleNamespace(),
        repairs=SimpleNamespace(get_by_id_for_user=AsyncMock(return_value=record)),
        workflow_builder=workflow_builder,
        jobs=jobs,
    )

    with pytest.raises(
        CustomerSupportRepairLaunchError,
        match="workflow is invalid",
    ):
        await coordinator.launch(
            user_id=record.user_id,
            repair_execution_id=record.id,
        )

    jobs.enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_launch_job_requires_user():
    ctx = SimpleNamespace(
        db=SimpleNamespace(),
        job=SimpleNamespace(
            user_id=None,
        ),
    )

    with pytest.raises(
        ValueError,
        match="requires user_id",
    ):
        await launch_customer_support_objective_repair_job(
            {"repair_execution_id": str(uuid4())},
            ctx,
        )


def test_repair_launch_job_is_registered():
    registry = SimpleNamespace(register=Mock())

    register_customer_service_job_handlers(registry)

    registrations = {
        call.args[0]: call.args[1] for call in registry.register.call_args_list
    }

    assert (
        registrations[CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB]
        is launch_customer_support_objective_repair_job
    )
