from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.workflow_operations.waits.service import (
    WorkflowWaitService,
)


def _query_result(*records):
    scalars = SimpleNamespace(
        all=lambda: list(records)
    )

    return SimpleNamespace(
        scalars=lambda: scalars
    )


@pytest.mark.asyncio
async def test_repair_resume_extras_use_durable_repair_record():
    user_id = uuid4()
    repair_id = uuid4()

    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=_query_result(
                SimpleNamespace(id=repair_id)
            )
        )
    )

    extras = await WorkflowWaitService(
        db
    )._repair_resume_extras(
        user_id=user_id,
        workflow_run_id="repair-run-1",
    )

    assert extras == {
        "customer_service": True,
        "objective_repair": {
            "repair_execution_id": str(
                repair_id
            ),
        },
    }

    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_generic_workflow_resume_has_empty_extras():
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=_query_result()
        )
    )

    extras = await WorkflowWaitService(
        db
    )._repair_resume_extras(
        user_id=uuid4(),
        workflow_run_id="generic-run-1",
    )

    assert extras == {}


@pytest.mark.asyncio
async def test_empty_workflow_run_id_has_empty_extras():
    db = SimpleNamespace(
        execute=AsyncMock()
    )

    extras = await WorkflowWaitService(
        db
    )._repair_resume_extras(
        user_id=uuid4(),
        workflow_run_id="",
    )

    assert extras == {}
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_repair_run_lineage_is_rejected():
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=_query_result(
                SimpleNamespace(id=uuid4()),
                SimpleNamespace(id=uuid4()),
            )
        )
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Multiple objective repair executions "
            "share the same workflow_run_id"
        ),
    ):
        await WorkflowWaitService(
            db
        )._repair_resume_extras(
            user_id=uuid4(),
            workflow_run_id="duplicate-run",
        )


@pytest.mark.asyncio
async def test_resolve_adds_repair_extras_to_resume_job():
    user_id = uuid4()
    repair_id = uuid4()
    wait_id = uuid4()

    wait = SimpleNamespace(
        id=wait_id,
        user_id=user_id,
        workflow_run_id="repair-run-resolve",
        wait_type="approval",
        node_id="approval",
        resolution={
            "approved": True,
        },
        status="resolved",
    )

    service = WorkflowWaitService(
        SimpleNamespace()
    )
    service.repo = SimpleNamespace(
        resolve_waiting=AsyncMock(
            return_value=wait
        )
    )
    service.jobs = SimpleNamespace(
        enqueue=AsyncMock(
            return_value=SimpleNamespace(
                id=uuid4()
            )
        )
    )
    service._repair_resume_extras = AsyncMock(
        return_value={
            "customer_service": True,
            "objective_repair": {
                "repair_execution_id": str(
                    repair_id
                ),
            },
        }
    )

    result = await service.resolve(
        user_id=user_id,
        wait_id=wait_id,
        resolution={
            "approved": True,
        },
        resume=True,
    )

    assert result["resume_job_id"]

    kwargs = (
        service.jobs.enqueue.await_args.kwargs
    )

    assert kwargs["job_type"] == (
        "workflow.resume"
    )
    assert kwargs["payload"][
        "workflow_run_id"
    ] == "repair-run-resolve"
    assert kwargs["payload"]["extras"] == {
        "customer_service": True,
        "objective_repair": {
            "repair_execution_id": str(
                repair_id
            ),
        },
    }

    service._repair_resume_extras.assert_awaited_once_with(
        user_id=user_id,
        workflow_run_id="repair-run-resolve",
    )


@pytest.mark.asyncio
async def test_approve_adds_repair_extras_to_resume_job():
    user_id = uuid4()
    repair_id = uuid4()
    wait_id = uuid4()

    wait = SimpleNamespace(
        id=wait_id,
        user_id=user_id,
        workflow_run_id="repair-run-approve",
        wait_type="approval",
        node_id="approval",
        resolution={
            "approved": True,
            "action": "approved",
        },
        status="resolved",
    )

    service = WorkflowWaitService(
        SimpleNamespace()
    )
    service.resolve = AsyncMock(
        return_value={
            "wait": wait,
            "resume_job": None,
        }
    )
    service.jobs = SimpleNamespace(
        enqueue=AsyncMock(
            return_value=SimpleNamespace(
                id=uuid4()
            )
        )
    )
    service._repair_resume_extras = AsyncMock(
        return_value={
            "customer_service": True,
            "objective_repair": {
                "repair_execution_id": str(
                    repair_id
                ),
            },
        }
    )

    result = await service.approve(
        user_id=user_id,
        wait_id=wait_id,
    )

    kwargs = (
        service.jobs.enqueue.await_args.kwargs
    )

    assert kwargs["payload"]["input"][
        "approved"
    ] is True
    assert kwargs["payload"]["extras"][
        "objective_repair"
    ]["repair_execution_id"] == str(
        repair_id
    )
    assert result["resume_job"] is not None


@pytest.mark.asyncio
async def test_reject_adds_repair_extras_to_resume_job():
    user_id = uuid4()
    repair_id = uuid4()
    wait_id = uuid4()

    wait = SimpleNamespace(
        id=wait_id,
        user_id=user_id,
        workflow_run_id="repair-run-reject",
        wait_type="approval",
        node_id="approval",
        resolution={
            "approved": False,
            "action": "rejected",
        },
        status="resolved",
    )

    service = WorkflowWaitService(
        SimpleNamespace()
    )
    service.resolve = AsyncMock(
        return_value={
            "wait": wait,
            "resume_job": None,
        }
    )
    service.jobs = SimpleNamespace(
        enqueue=AsyncMock(
            return_value=SimpleNamespace(
                id=uuid4()
            )
        )
    )
    service._repair_resume_extras = AsyncMock(
        return_value={
            "customer_service": True,
            "objective_repair": {
                "repair_execution_id": str(
                    repair_id
                ),
            },
        }
    )

    result = await service.reject(
        user_id=user_id,
        wait_id=wait_id,
    )

    kwargs = (
        service.jobs.enqueue.await_args.kwargs
    )

    assert kwargs["payload"]["input"][
        "approved"
    ] is False
    assert kwargs["payload"]["extras"][
        "objective_repair"
    ]["repair_execution_id"] == str(
        repair_id
    )
    assert result["resume_job"] is not None


@pytest.mark.asyncio
async def test_expire_adds_repair_extras_to_resume_job():
    user_id = uuid4()
    repair_id = uuid4()

    wait = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        workflow_run_id="repair-run-expire",
        wait_type="time",
        node_id="wait",
        status="waiting",
        resolution=None,
        resolved_at=None,
    )

    service = WorkflowWaitService(
        SimpleNamespace()
    )
    service.repo = SimpleNamespace(
        save=AsyncMock(
            return_value=wait
        )
    )
    service.jobs = SimpleNamespace(
        enqueue=AsyncMock(
            return_value=SimpleNamespace(
                id=uuid4()
            )
        )
    )
    service._repair_resume_extras = AsyncMock(
        return_value={
            "customer_service": True,
            "objective_repair": {
                "repair_execution_id": str(
                    repair_id
                ),
            },
        }
    )

    await service.expire(
        wait=wait
    )

    kwargs = (
        service.jobs.enqueue.await_args.kwargs
    )

    assert kwargs["payload"]["input"][
        "expired"
    ] is True
    assert kwargs["payload"]["extras"][
        "objective_repair"
    ]["repair_execution_id"] == str(
        repair_id
    )
