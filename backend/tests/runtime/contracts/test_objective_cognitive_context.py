from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.runtime.objectives.cognition import (
    ObjectiveCognitiveContext,
    ObjectiveCognitiveContextLoader,
    ObjectiveCognitiveIdentity,
    ObjectiveCognitiveSafety,
)


NOW = datetime(
    2026,
    8,
    3,
    8,
    0,
    tzinfo=timezone.utc,
)


def _resolution(
    *,
    user_id=None,
    tenant_id="tenant-1",
):
    return SimpleNamespace(
        id=uuid4(),
        source_event_id=uuid4(),
        user_id=user_id or uuid4(),
        tenant_id=tenant_id,
        objective_namespace=(
            "customer_service.support"
        ),
        objective_type="multi_operation",
        objective_ref="review-plan-1",
        objective_version=3,
        source_outcome_ref="outcome-1",
        outcome_version=1,
        source_evaluation_ref="evaluation-1",
        evaluation_version=1,
        projection_version=1,
        workflow_run_id="workflow-run-1",
        status="failed",
        reason_code=(
            "one_or_more_operations_failed"
        ),
        summary="The refund operation failed.",
        confidence=0.95,
        is_terminal=False,
        operation_count=2,
        achieved_operation_count=1,
        unresolved_operation_count=1,
        failed_operation_count=1,
        pending_operation_count=0,
        unknown_operation_count=0,
        not_executed_operation_count=0,
        assessment_json={
            "unresolved_operation_refs": [
                "operation-refund",
            ],
            "failed_operation_refs": [
                "operation-refund",
            ],
            "pending_operation_refs": [],
            "unknown_operation_refs": [],
            "not_executed_operation_refs": [],
            "secret_provider_payload": {
                "must_not_be_copied": True,
            },
        },
        created_at=NOW,
    )


def _repair(
    *,
    resolution_record_id,
    status="rejected",
):
    return SimpleNamespace(
        id=uuid4(),
        resolution_record_id=(
            resolution_record_id
        ),
        source_event_id=uuid4(),
        status=status,
        attempt_number=2,
        repair_request_ref=(
            "objective-repair:resolution:v1"
        ),
        repair_request_version=1,
        planner_ref=(
            "customer_support_objective_repair"
        ),
        planner_policy_version=1,
        disposition="replan_remaining",
        reason_code=(
            "support_repair_requires_replanning"
        ),
        summary=(
            "Rebuild the failed refund operation."
        ),
        confidence=0.92,
        automatic_execution_allowed=False,
        human_approval_required=True,
        workflow_job_id=uuid4(),
        workflow_run_id="repair-run-1",
        result_json={
            "meta": {
                "status": "ok",
                "final_state": {
                    "vars": {
                        "repair_result": {
                            "status": "rejected",
                            "provider_secret": (
                                "must-not-be-copied"
                            ),
                        },
                    },
                },
            },
        },
        failure_code=None,
        failure_message=None,
        created_at=NOW,
        completed_at=NOW,
    )


@pytest.mark.asyncio
async def test_loader_returns_absent_context_without_resolution():
    user_id = uuid4()

    resolution_repository = SimpleNamespace(
        get_latest_for_objective=AsyncMock(
            return_value=None
        )
    )
    repair_repository = SimpleNamespace(
        get_latest_for_resolution=AsyncMock()
    )

    context = await ObjectiveCognitiveContextLoader(
        SimpleNamespace(),
        resolution_repository=(
            resolution_repository
        ),
        repair_repository=repair_repository,
    ).load_for_objective(
        user_id=user_id,
        objective_namespace=(
            "CUSTOMER_SERVICE.SUPPORT"
        ),
        objective_ref="review-plan-1",
    )

    assert context.present is False
    assert context.resolution is None
    assert context.latest_repair is None
    assert context.identity.namespace == (
        "customer_service.support"
    )

    (
        repair_repository
        .get_latest_for_resolution
        .assert_not_awaited()
    )


@pytest.mark.asyncio
async def test_loader_normalizes_latest_resolution_and_repair():
    user_id = uuid4()
    resolution = _resolution(
        user_id=user_id
    )
    repair = _repair(
        resolution_record_id=resolution.id
    )

    resolution_repository = SimpleNamespace(
        get_latest_for_objective=AsyncMock(
            return_value=resolution
        )
    )
    repair_repository = SimpleNamespace(
        get_latest_for_resolution=AsyncMock(
            return_value=repair
        )
    )

    context = await ObjectiveCognitiveContextLoader(
        SimpleNamespace(),
        resolution_repository=(
            resolution_repository
        ),
        repair_repository=repair_repository,
    ).load_for_objective(
        user_id=user_id,
        objective_namespace=(
            "customer_service.support"
        ),
        objective_ref="review-plan-1",
        tenant_id="tenant-1",
    )

    assert context.present is True
    assert context.identity == (
        ObjectiveCognitiveIdentity(
            namespace=(
                "customer_service.support"
            ),
            objective_ref="review-plan-1",
            objective_type="multi_operation",
            objective_version=3,
        )
    )

    assert context.resolution is not None
    assert (
        context.resolution
        .unresolved_operation_refs
        == ("operation-refund",)
    )
    assert (
        context.resolution
        .failed_operation_refs
        == ("operation-refund",)
    )

    assert context.latest_repair is not None
    assert context.latest_repair.status == (
        "rejected"
    )
    assert (
        context.latest_repair.runtime_status
        == "ok"
    )
    assert (
        context.latest_repair
        .repair_result_status
        == "rejected"
    )

    dumped = context.model_dump(
        mode="json"
    )

    assert "secret_provider_payload" not in str(
        dumped
    )
    assert "provider_secret" not in str(
        dumped
    )

    (
        repair_repository
        .get_latest_for_resolution
        .assert_awaited_once_with(
            user_id=user_id,
            resolution_record_id=(
                resolution.id
            ),
        )
    )


@pytest.mark.asyncio
async def test_loader_enforces_requested_tenant_scope():
    user_id = uuid4()
    resolution = _resolution(
        user_id=user_id,
        tenant_id="tenant-other",
    )

    repair_repository = SimpleNamespace(
        get_latest_for_resolution=AsyncMock()
    )

    context = await ObjectiveCognitiveContextLoader(
        SimpleNamespace(),
        resolution_repository=SimpleNamespace(
            get_latest_for_objective=(
                AsyncMock(
                    return_value=resolution
                )
            )
        ),
        repair_repository=repair_repository,
    ).load_for_objective(
        user_id=user_id,
        objective_namespace=(
            "customer_service.support"
        ),
        objective_ref="review-plan-1",
        tenant_id="tenant-1",
    )

    assert context.present is False

    (
        repair_repository
        .get_latest_for_resolution
        .assert_not_awaited()
    )


@pytest.mark.asyncio
async def test_loader_keeps_context_without_repair():
    user_id = uuid4()
    resolution = _resolution(
        user_id=user_id
    )

    context = await ObjectiveCognitiveContextLoader(
        SimpleNamespace(),
        resolution_repository=SimpleNamespace(
            get_latest_for_objective=(
                AsyncMock(
                    return_value=resolution
                )
            )
        ),
        repair_repository=SimpleNamespace(
            get_latest_for_resolution=(
                AsyncMock(return_value=None)
            )
        ),
    ).load_for_objective(
        user_id=user_id,
        objective_namespace=(
            "customer_service.support"
        ),
        objective_ref="review-plan-1",
    )

    assert context.present is True
    assert context.resolution is not None
    assert context.latest_repair is None
    assert (
        context.provenance
        .repair_execution_id
        is None
    )


def test_context_is_immutable():
    context = ObjectiveCognitiveContext(
        present=False,
        identity=ObjectiveCognitiveIdentity(
            namespace="test.objective",
            objective_ref="objective-1",
        ),
        provenance={
            "source": (
                "durable_objective_records"
            ),
        },
    )

    with pytest.raises(ValidationError):
        context.present = True


def test_safety_contract_rejects_decision_authority():
    with pytest.raises(
        ValidationError,
        match=(
            "cannot alter planning or "
            "execution decisions"
        ),
    ):
        ObjectiveCognitiveSafety(
            affects_ranking=True
        )


@pytest.mark.asyncio
async def test_repair_repository_selects_latest_attempt():
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=SimpleNamespace(
                scalar_one_or_none=lambda: None
            )
        )
    )

    from app.runtime.objectives.repair.repository import (
        ObjectiveRepairExecutionRepository,
    )

    result = await (
        ObjectiveRepairExecutionRepository(
            db
        ).get_latest_for_resolution(
            user_id=uuid4(),
            resolution_record_id=uuid4(),
        )
    )

    assert result is None
    db.execute.assert_awaited_once()

    statement = (
        db.execute.await_args.args[0]
    )
    compiled = str(statement)

    assert (
        "objective_repair_executions"
        in compiled
    )
    assert "user_id" in compiled
    assert "resolution_record_id" in compiled
    assert "attempt_number DESC" in compiled
    assert "LIMIT" in compiled


def test_loader_uses_no_commit_boundary():
    source = (
        __import__(
            "pathlib"
        )
        .Path(
            'app/runtime/objectives/cognition/loader.py'
        )
        .read_text(encoding="utf-8")
    )

    assert ".commit(" not in source
    assert ".flush(" not in source
    assert ".add(" not in source
