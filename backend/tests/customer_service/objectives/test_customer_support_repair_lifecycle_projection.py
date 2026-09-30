from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domains.customer_service.services.support.repair.lifecycle_projection import (
    CustomerSupportRepairLifecycleProjectionError,
    CustomerSupportRepairLifecycleProjector,
)
from app.runtime.objectives.repair import (
    OBJECTIVE_REPAIR_EXECUTION_STATUS_COMPLETED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_FAILED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_REJECTED,
)


def _job(
    *,
    user_id,
    repair_execution_id,
    status="succeeded",
    result=None,
    job_type="workflow.run",
    workflow_run_id=None,
):
    payload = {
        "extras": {
            "customer_service": True,
            "objective_repair": {
                "repair_execution_id": str(
                    repair_execution_id
                ),
            },
        },
    }

    if workflow_run_id is not None:
        payload["workflow_run_id"] = (
            workflow_run_id
        )

    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        job_type=job_type,
        status=status,
        payload=payload,
        result=result,
        error_message=None,
        attempts=1,
        max_attempts=5,
    )


def _repair(
    *,
    user_id,
    job_id,
    status=(
        OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED
    ),
    workflow_run_id=None,
):
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        workflow_job_id=job_id,
        workflow_run_id=workflow_run_id,
        status=status,
        result_json=None,
        failure_code=None,
        failure_message=None,
    )


def _runtime_result(
    *,
    workflow_run_id,
    status,
    repair_status=None,
):
    variables = {}

    if repair_status is not None:
        variables["repair_result"] = {
            "status": repair_status,
        }

    return {
        "answer": None,
        "meta": {
            "status": status,
            "workflow_run_id": workflow_run_id,
            "final_state": {
                "workflow_run_id": (
                    workflow_run_id
                ),
                "vars": variables,
            },
        },
    }


@pytest.mark.asyncio
async def test_projects_paused_workflow():
    user_id = uuid4()
    repair_id = uuid4()
    workflow_run_id = str(uuid4())

    job = _job(
        user_id=user_id,
        repair_execution_id=repair_id,
        result=_runtime_result(
            workflow_run_id=workflow_run_id,
            status="paused",
        ),
    )
    repair = _repair(
        user_id=user_id,
        job_id=job.id,
    )
    repair.id = repair_id

    running = SimpleNamespace(
        **{
            **repair.__dict__,
            "status": "running",
            "workflow_run_id": workflow_run_id,
        }
    )
    paused = SimpleNamespace(
        **{
            **running.__dict__,
            "status": (
                OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED
            ),
        }
    )

    lifecycle = SimpleNamespace(
        mark_running=AsyncMock(
            return_value=running
        ),
        mark_paused=AsyncMock(
            return_value=paused
        ),
    )
    db = SimpleNamespace(
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await (
        CustomerSupportRepairLifecycleProjector(
            db,
            jobs=SimpleNamespace(
                get=AsyncMock(return_value=job)
            ),
            repairs=SimpleNamespace(
                get_by_id_for_user=AsyncMock(
                    return_value=repair
                )
            ),
            lifecycle=lifecycle,
        ).project_succeeded_job(
            user_id=user_id,
            workflow_job_id=job.id,
        )
    )

    assert result.projected is True
    assert result.reason == "workflow_paused"
    assert result.repair_execution.status == (
        OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED
    )

    lifecycle.mark_running.assert_awaited_once()
    lifecycle.mark_paused.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_projects_completed_workflow():
    user_id = uuid4()
    repair_id = uuid4()
    workflow_run_id = str(uuid4())

    job = _job(
        user_id=user_id,
        repair_execution_id=repair_id,
        result=_runtime_result(
            workflow_run_id=workflow_run_id,
            status="ok",
            repair_status=(
                "provider_operations_completed"
            ),
        ),
    )
    repair = _repair(
        user_id=user_id,
        job_id=job.id,
    )
    repair.id = repair_id

    completed = SimpleNamespace(
        **{
            **repair.__dict__,
            "status": (
                OBJECTIVE_REPAIR_EXECUTION_STATUS_COMPLETED
            ),
            "workflow_run_id": workflow_run_id,
        }
    )

    lifecycle = SimpleNamespace(
        mark_running=AsyncMock(
            return_value=SimpleNamespace(
                **{
                    **repair.__dict__,
                    "status": "running",
                    "workflow_run_id": (
                        workflow_run_id
                    ),
                }
            )
        ),
        mark_completed=AsyncMock(
            return_value=completed
        ),
    )

    result = await (
        CustomerSupportRepairLifecycleProjector(
            SimpleNamespace(
                commit=AsyncMock(),
                refresh=AsyncMock(),
            ),
            jobs=SimpleNamespace(
                get=AsyncMock(return_value=job)
            ),
            repairs=SimpleNamespace(
                get_by_id_for_user=AsyncMock(
                    return_value=repair
                )
            ),
            lifecycle=lifecycle,
        ).project_succeeded_job(
            user_id=user_id,
            workflow_job_id=job.id,
        )
    )

    assert result.reason == "workflow_completed"
    lifecycle.mark_completed.assert_awaited_once()


@pytest.mark.asyncio
async def test_projects_rejected_workflow():
    user_id = uuid4()
    repair_id = uuid4()
    workflow_run_id = str(uuid4())

    job = _job(
        user_id=user_id,
        repair_execution_id=repair_id,
        result=_runtime_result(
            workflow_run_id=workflow_run_id,
            status="ok",
            repair_status="rejected",
        ),
    )
    repair = _repair(
        user_id=user_id,
        job_id=job.id,
    )
    repair.id = repair_id

    rejected = SimpleNamespace(
        **{
            **repair.__dict__,
            "status": (
                OBJECTIVE_REPAIR_EXECUTION_STATUS_REJECTED
            ),
            "workflow_run_id": workflow_run_id,
        }
    )

    lifecycle = SimpleNamespace(
        mark_running=AsyncMock(
            return_value=SimpleNamespace(
                **{
                    **repair.__dict__,
                    "status": "running",
                    "workflow_run_id": (
                        workflow_run_id
                    ),
                }
            )
        ),
        mark_rejected=AsyncMock(
            return_value=rejected
        ),
    )

    result = await (
        CustomerSupportRepairLifecycleProjector(
            SimpleNamespace(
                commit=AsyncMock(),
                refresh=AsyncMock(),
            ),
            jobs=SimpleNamespace(
                get=AsyncMock(return_value=job)
            ),
            repairs=SimpleNamespace(
                get_by_id_for_user=AsyncMock(
                    return_value=repair
                )
            ),
            lifecycle=lifecycle,
        ).project_succeeded_job(
            user_id=user_id,
            workflow_job_id=job.id,
        )
    )

    assert result.reason == "workflow_rejected"
    lifecycle.mark_rejected.assert_awaited_once()


@pytest.mark.asyncio
async def test_dead_letter_projects_failed():
    user_id = uuid4()
    repair_id = uuid4()

    job = _job(
        user_id=user_id,
        repair_execution_id=repair_id,
        status="dead_letter",
        result=None,
    )
    job.error_message = "provider unavailable"
    job.attempts = 5

    repair = _repair(
        user_id=user_id,
        job_id=job.id,
    )
    repair.id = repair_id

    failed = SimpleNamespace(
        **{
            **repair.__dict__,
            "status": (
                OBJECTIVE_REPAIR_EXECUTION_STATUS_FAILED
            ),
            "failure_code": (
                "workflow_job_dead_lettered"
            ),
            "failure_message": (
                "provider unavailable"
            ),
        }
    )

    lifecycle = SimpleNamespace(
        mark_failed=AsyncMock(
            return_value=failed
        )
    )

    result = await (
        CustomerSupportRepairLifecycleProjector(
            SimpleNamespace(
                commit=AsyncMock(),
                refresh=AsyncMock(),
            ),
            jobs=SimpleNamespace(
                get=AsyncMock(return_value=job)
            ),
            repairs=SimpleNamespace(
                get_by_id_for_user=AsyncMock(
                    return_value=repair
                )
            ),
            lifecycle=lifecycle,
        ).project_dead_lettered_job(
            user_id=user_id,
            workflow_job_id=job.id,
        )
    )

    assert result.reason == (
        "workflow_job_dead_lettered"
    )
    lifecycle.mark_failed.assert_awaited_once()


@pytest.mark.asyncio
async def test_retryable_failure_does_not_fail_repair():
    user_id = uuid4()
    repair_id = uuid4()

    job = _job(
        user_id=user_id,
        repair_execution_id=repair_id,
        status="queued",
    )
    repair = _repair(
        user_id=user_id,
        job_id=job.id,
    )
    repair.id = repair_id

    lifecycle = SimpleNamespace(
        mark_failed=AsyncMock()
    )

    result = await (
        CustomerSupportRepairLifecycleProjector(
            SimpleNamespace(),
            jobs=SimpleNamespace(
                get=AsyncMock(return_value=job)
            ),
            repairs=SimpleNamespace(
                get_by_id_for_user=AsyncMock(
                    return_value=repair
                )
            ),
            lifecycle=lifecycle,
        ).project_retryable_failed_job(
            user_id=user_id,
            workflow_job_id=job.id,
        )
    )

    assert result.projected is False
    assert result.reason == (
        "workflow_job_retry_scheduled"
    )
    lifecycle.mark_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_repair_job_is_ignored():
    user_id = uuid4()
    job = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        job_type="workflow.run",
        status="succeeded",
        payload={"extras": {}},
        result={},
    )

    result = await (
        CustomerSupportRepairLifecycleProjector(
            SimpleNamespace(),
            jobs=SimpleNamespace(
                get=AsyncMock(return_value=job)
            ),
        ).project_succeeded_job(
            user_id=user_id,
            workflow_job_id=job.id,
        )
    )

    assert result.projected is False
    assert result.reason == (
        "job_is_not_objective_repair"
    )


@pytest.mark.asyncio
async def test_job_lineage_mismatch_is_rejected():
    user_id = uuid4()
    repair_id = uuid4()
    workflow_run_id = str(uuid4())

    job = _job(
        user_id=user_id,
        repair_execution_id=repair_id,
        result=_runtime_result(
            workflow_run_id=workflow_run_id,
            status="ok",
        ),
    )
    repair = _repair(
        user_id=user_id,
        job_id=uuid4(),
    )
    repair.id = repair_id

    with pytest.raises(
        CustomerSupportRepairLifecycleProjectionError,
        match="does not match",
    ):
        await (
            CustomerSupportRepairLifecycleProjector(
                SimpleNamespace(),
                jobs=SimpleNamespace(
                    get=AsyncMock(return_value=job)
                ),
                repairs=SimpleNamespace(
                    get_by_id_for_user=AsyncMock(
                        return_value=repair
                    )
                ),
            ).project_succeeded_job(
                user_id=user_id,
                workflow_job_id=job.id,
            )
        )


@pytest.mark.asyncio
async def test_job_is_user_scoped():
    owner_id = uuid4()
    other_user_id = uuid4()

    job = _job(
        user_id=owner_id,
        repair_execution_id=uuid4(),
        result={},
    )

    with pytest.raises(
        CustomerSupportRepairLifecycleProjectionError,
        match="not found for user",
    ):
        await (
            CustomerSupportRepairLifecycleProjector(
                SimpleNamespace(),
                jobs=SimpleNamespace(
                    get=AsyncMock(return_value=job)
                ),
            ).project_succeeded_job(
                user_id=other_user_id,
                workflow_job_id=job.id,
            )
        )
