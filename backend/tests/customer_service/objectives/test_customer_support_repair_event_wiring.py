from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.domains.customer_service.events.handlers import (
    CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB,
    CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_PLANNED_EVENT,
    enqueue_customer_support_objective_repair_launch,
    project_customer_support_repair_job_dead_lettered,
    project_customer_support_repair_job_failed,
    project_customer_support_repair_job_succeeded,
    register_customer_service_event_handlers,
)


def _event(
    event_type,
    *,
    user_id=None,
    payload=None,
):
    return SimpleNamespace(
        id=uuid4(),
        event_type=event_type,
        user_id=user_id,
        payload=payload or {},
    )


@pytest.mark.asyncio
async def test_planned_event_enqueues_launch_job_without_commit():
    user_id = uuid4()
    repair_execution_id = uuid4()
    event = _event(
        CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_PLANNED_EVENT,
        user_id=user_id,
        payload={
            "repair_execution_id": str(repair_execution_id),
        },
    )

    job = SimpleNamespace(
        id=uuid4(),
        job_type=(CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB),
    )

    with patch("app.platform.jobs.service.JobService") as service_type:
        service_type.return_value.enqueue = AsyncMock(return_value=job)

        result = await enqueue_customer_support_objective_repair_launch(
            event,
            SimpleNamespace(db=object()),
        )

    assert result["scheduled"] is True

    kwargs = service_type.return_value.enqueue.await_args.kwargs

    assert kwargs["user_id"] == user_id
    assert kwargs["job_type"] == (CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB)
    assert kwargs["commit"] is False
    assert kwargs["max_attempts"] == 5
    assert kwargs["payload"]["repair_execution_id"] == str(repair_execution_id)
    assert kwargs["idempotency_key"] == (
        f"customer-support-objective-repair-launch:{repair_execution_id}"
    )


@pytest.mark.asyncio
async def test_planned_event_without_user_is_skipped():
    result = await enqueue_customer_support_objective_repair_launch(
        _event(
            CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_PLANNED_EVENT,
            payload={
                "repair_execution_id": str(uuid4()),
            },
        ),
        SimpleNamespace(db=object()),
    )

    assert result["scheduled"] is False
    assert result["reason"] == ("event_user_id_missing")


@pytest.mark.asyncio
async def test_succeeded_event_calls_projector():
    user_id = uuid4()
    job_id = uuid4()
    repair_id = uuid4()

    event = _event(
        "job.succeeded",
        user_id=user_id,
        payload={
            "job_id": str(job_id),
            "job_type": "workflow.run",
        },
    )

    projection = SimpleNamespace(
        projected=True,
        reason="workflow_completed",
        workflow_job_id=job_id,
        repair_execution=SimpleNamespace(id=repair_id),
    )

    with patch(
        "app.domains.customer_service.services."
        "support.repair.lifecycle_projection."
        "CustomerSupportRepairLifecycleProjector"
    ) as projector_type:
        projector_type.return_value.project_succeeded_job = AsyncMock(
            return_value=projection
        )

        result = await project_customer_support_repair_job_succeeded(
            event,
            SimpleNamespace(db=object()),
        )

    assert result["projected"] is True
    assert result["repair_execution_id"] == str(repair_id)

    (
        projector_type.return_value.project_succeeded_job.assert_awaited_once_with(
            user_id=user_id,
            workflow_job_id=job_id,
        )
    )


@pytest.mark.asyncio
async def test_retryable_failed_event_calls_nonterminal_projection():
    user_id = uuid4()
    job_id = uuid4()

    event = _event(
        "job.failed",
        user_id=user_id,
        payload={
            "job_id": str(job_id),
            "job_type": "workflow.resume",
            "status": "queued",
        },
    )

    projection = SimpleNamespace(
        projected=False,
        reason="workflow_job_retry_scheduled",
        workflow_job_id=job_id,
        repair_execution=None,
    )

    with patch(
        "app.domains.customer_service.services."
        "support.repair.lifecycle_projection."
        "CustomerSupportRepairLifecycleProjector"
    ) as projector_type:
        (projector_type.return_value.project_retryable_failed_job) = AsyncMock(
            return_value=projection
        )

        result = await project_customer_support_repair_job_failed(
            event,
            SimpleNamespace(db=object()),
        )

    assert result["projected"] is False
    assert result["reason"] == ("workflow_job_retry_scheduled")


@pytest.mark.asyncio
async def test_nonretryable_failed_event_is_ignored():
    event = _event(
        "job.failed",
        user_id=uuid4(),
        payload={
            "job_id": str(uuid4()),
            "job_type": "workflow.run",
            "status": "dead_letter",
        },
    )

    result = await project_customer_support_repair_job_failed(
        event,
        SimpleNamespace(db=object()),
    )

    assert result["projected"] is False
    assert result["reason"] == ("job_failure_is_not_retryable")


@pytest.mark.asyncio
async def test_dead_letter_event_calls_terminal_projection():
    user_id = uuid4()
    job_id = uuid4()

    event = _event(
        "job.dead_lettered",
        user_id=user_id,
        payload={
            "job_id": str(job_id),
            "job_type": "workflow.run",
            "error_message": "provider unavailable",
        },
    )

    projection = SimpleNamespace(
        projected=True,
        reason="workflow_job_dead_lettered",
        workflow_job_id=job_id,
        repair_execution=SimpleNamespace(id=uuid4()),
    )

    with patch(
        "app.domains.customer_service.services."
        "support.repair.lifecycle_projection."
        "CustomerSupportRepairLifecycleProjector"
    ) as projector_type:
        (projector_type.return_value.project_dead_lettered_job) = AsyncMock(
            return_value=projection
        )

        await project_customer_support_repair_job_dead_lettered(
            event,
            SimpleNamespace(db=object()),
        )

    (
        projector_type.return_value.project_dead_lettered_job.assert_awaited_once_with(
            user_id=user_id,
            workflow_job_id=job_id,
            error_message="provider unavailable",
        )
    )


@pytest.mark.asyncio
async def test_nonworkflow_job_is_ignored():
    event = _event(
        "job.succeeded",
        user_id=uuid4(),
        payload={
            "job_id": str(uuid4()),
            "job_type": "test.echo",
        },
    )

    result = await project_customer_support_repair_job_succeeded(
        event,
        SimpleNamespace(db=object()),
    )

    assert result["projected"] is False
    assert result["reason"] == ("job_type_not_supported")


def test_repair_event_handlers_are_registered():
    registry = SimpleNamespace(subscribe=Mock())

    register_customer_service_event_handlers(registry)

    registrations = {call.args for call in registry.subscribe.call_args_list}

    assert (
        CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_PLANNED_EVENT,
        enqueue_customer_support_objective_repair_launch,
    ) in registrations

    assert (
        "job.succeeded",
        project_customer_support_repair_job_succeeded,
    ) in registrations

    assert (
        "job.failed",
        project_customer_support_repair_job_failed,
    ) in registrations

    assert (
        "job.dead_lettered",
        project_customer_support_repair_job_dead_lettered,
    ) in registrations
