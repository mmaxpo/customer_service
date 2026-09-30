from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.models.models import (
    ObjectiveRepairExecutionRecord,
    PlatformEvent,
)
from app.platform.events.event_store import (
    PlatformEventStore,
)
from app.runtime.objectives.repair import (
    OBJECTIVE_REPAIR_PLANNED_EVENT,
    ObjectiveRepairAction,
    ObjectiveRepairConstraints,
    ObjectiveRepairDisposition,
    ObjectiveRepairExecutionConflictError,
    ObjectiveRepairExecutionRepository,
    ObjectiveRepairExecutionService,
    ObjectiveRepairPlan,
    ObjectiveRepairRequest,
    ObjectiveRepairSource,
    ObjectiveRepairTarget,
)
from app.runtime.objectives.resolution import (
    ObjectiveOperationResolution,
    ObjectiveOperationStatus,
    ObjectiveReference,
    ObjectiveResolutionAssessment,
    ObjectiveResolutionService,
    ObjectiveResolutionSource,
    ObjectiveResolutionStatus,
)


def _objective():
    return ObjectiveReference(
        namespace="customer_service.support",
        objective_type="multi_operation",
        objective_ref="review-1",
        objective_version=1,
    )


def _request():
    return ObjectiveRepairRequest(
        repair_request_ref=(
            "objective-repair:resolution-1:v1"
        ),
        source=ObjectiveRepairSource(
            resolution_record_ref="resolution-1",
            objective=_objective(),
            outcome_ref="outcome-1",
            outcome_version=1,
            evaluation_ref="evaluation-1",
            evaluation_version=1,
            resolution_projection_version=1,
            workflow_run_id="source-run-1",
        ),
        resolution_status=(
            ObjectiveResolutionStatus.FAILED
        ),
        resolution_reason_code=(
            "one_or_more_operations_failed"
        ),
        resolution_summary=(
            "One required support operation failed."
        ),
        resolution_confidence=0.9,
        targets=(
            ObjectiveRepairTarget(
                operation_ref="operation-1",
                operation_type="whole_refund",
                resolution_status=(
                    ObjectiveOperationStatus.FAILED
                ),
                required=True,
                reason_code="provider_failure",
                summary="Refund failed.",
                source_task_id="task-1",
                verification_ref="verification-1",
                evidence_refs=("evidence-1",),
            ),
        ),
        constraints=ObjectiveRepairConstraints(
            allow_automatic_execution=False,
            require_human_approval=False,
            allowed_dispositions=(
                ObjectiveRepairDisposition
                .REPLAN_REMAINING,
                ObjectiveRepairDisposition
                .REQUEST_HUMAN_ACTION,
                ObjectiveRepairDisposition
                .STOP_REPAIR,
            ),
        ),
    )


def _plan(
    *,
    summary=(
        "Replan the failed operation behind approval."
    ),
):
    return ObjectiveRepairPlan(
        repair_request_ref=(
            _request().repair_request_ref
        ),
        objective=_objective(),
        disposition=(
            ObjectiveRepairDisposition
            .REPLAN_REMAINING
        ),
        reason_code=(
            "support_repair_requires_replanning"
        ),
        summary=summary,
        confidence=0.9,
        actions=(
            ObjectiveRepairAction(
                action_ref=(
                    "support-repair:request:001:"
                    "replan_remaining:operation-1"
                ),
                disposition=(
                    ObjectiveRepairDisposition
                    .REPLAN_REMAINING
                ),
                target_operation_refs=(
                    "operation-1",
                ),
                reason_code=(
                    "support_operation_failed_"
                    "requires_replan"
                ),
                summary=(
                    "Rebuild the failed operation."
                ),
                confidence=0.9,
                automatic_execution_allowed=False,
                human_approval_required=True,
                planner_directives={
                    "require_new_human_approval": True,
                },
            ),
        ),
        planned_target_refs=(
            "operation-1",
        ),
        deferred_target_refs=(),
        unhandled_target_refs=(),
        automatic_execution_allowed=False,
        human_approval_required=True,
        planner_metadata={
            "planner": (
                "customer_support_objective_repair.v1"
            ),
            "policy_version": 1,
        },
    )


async def _source_event(
    db,
    *,
    user_id,
    suffix="1",
):
    return await PlatformEventStore(db).append(
        event_type=(
            "runtime.objective.resolution.assessed"
        ),
        source="runtime.objective_resolution",
        user_id=user_id,
        payload={
            "resolution_record_id": (
                f"resolution-{suffix}"
            ),
        },
        meta={},
    )


async def _resolution_record(
    db,
    *,
    user_id,
    source_event_id,
):
    assessment = ObjectiveResolutionAssessment(
        objective=_objective(),
        source=ObjectiveResolutionSource(
            outcome_ref="outcome-1",
            outcome_version=1,
            evaluation_ref="evaluation-1",
            evaluation_version=1,
            workflow_run_id="source-run-1",
        ),
        status=ObjectiveResolutionStatus.FAILED,
        reason_code=(
            "one_or_more_operations_failed"
        ),
        summary=(
            "One required support operation failed."
        ),
        confidence=0.9,
        is_terminal=False,
        operations=(
            ObjectiveOperationResolution(
                operation_ref="operation-1",
                operation_type="whole_refund",
                status=(
                    ObjectiveOperationStatus.FAILED
                ),
                required=True,
                reason_code="provider_failure",
                summary="Refund failed.",
                source_task_id="task-1",
                verification_ref="verification-1",
                evidence_refs=("evidence-1",),
            ),
        ),
    )

    write = await (
        ObjectiveResolutionService(db)
        .record_assessment(
            source_event_id=source_event_id,
            user_id=user_id,
            tenant_id="tenant-1",
            assessment=assessment,
            projection_version=1,
        )
    )

    return write.record


@pytest.mark.asyncio
async def test_records_repair_plan_and_emits_event():
    user_id = uuid4()

    async with SessionLocal() as db:
        resolution_source = await _source_event(
            db,
            user_id=user_id,
            suffix="resolution",
        )
        resolution = await _resolution_record(
            db,
            user_id=user_id,
            source_event_id=resolution_source.id,
        )
        repair_source = await _source_event(
            db,
            user_id=user_id,
            suffix="repair",
        )

        result = await (
            ObjectiveRepairExecutionService(db)
            .record_plan(
                source_event_id=repair_source.id,
                user_id=user_id,
                tenant_id="tenant-1",
                resolution_record_id=resolution.id,
                request=_request(),
                plan=_plan(),
                planner_ref=(
                    "customer_support_objective_repair"
                ),
                planner_policy_version=1,
                attempt_number=1,
            )
        )

    assert result.created is True
    assert result.event_id is not None
    assert result.record.status == "planned"
    assert result.record.attempt_number == 1
    assert result.record.target_count == 1
    assert (
        result.record.planned_target_count
        == 1
    )
    assert (
        result.record.requires_human_approval
        is True
    )
    assert (
        result.record.automatic_execution_allowed
        is False
    )
    assert result.record.workflow_job_id is None
    assert result.record.workflow_run_id is None
    assert result.record.workflow_json is None

    async with SessionLocal() as db:
        saved = await db.get(
            ObjectiveRepairExecutionRecord,
            result.record.id,
        )
        assert saved is not None
        assert saved.request_json[
            "repair_request_ref"
        ] == _request().repair_request_ref
        assert saved.plan_json["disposition"] == (
            "replan_remaining"
        )

        events = list(
            (
                await db.execute(
                    select(PlatformEvent).where(
                        PlatformEvent.user_id
                        == user_id,
                        PlatformEvent.event_type
                        == OBJECTIVE_REPAIR_PLANNED_EVENT,
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(events) == 1
        assert events[0].payload[
            "repair_execution_id"
        ] == str(saved.id)


@pytest.mark.asyncio
async def test_same_source_event_is_idempotent():
    user_id = uuid4()

    async with SessionLocal() as db:
        resolution_source = await _source_event(
            db,
            user_id=user_id,
            suffix="resolution",
        )
        resolution = await _resolution_record(
            db,
            user_id=user_id,
            source_event_id=resolution_source.id,
        )
        repair_source = await _source_event(
            db,
            user_id=user_id,
            suffix="repair",
        )

        service = ObjectiveRepairExecutionService(
            db
        )

        first = await service.record_plan(
            source_event_id=repair_source.id,
            user_id=user_id,
            tenant_id="tenant-1",
            resolution_record_id=resolution.id,
            request=_request(),
            plan=_plan(),
            planner_ref=(
                "customer_support_objective_repair"
            ),
            planner_policy_version=1,
        )

        second = await service.record_plan(
            source_event_id=repair_source.id,
            user_id=user_id,
            tenant_id="tenant-1",
            resolution_record_id=resolution.id,
            request=_request(),
            plan=_plan(),
            planner_ref=(
                "customer_support_objective_repair"
            ),
            planner_policy_version=1,
        )

    assert first.created is True
    assert second.created is False
    assert first.record.id == second.record.id
    assert second.event_id is None

    async with SessionLocal() as db:
        rows = list(
            (
                await db.execute(
                    select(
                        ObjectiveRepairExecutionRecord
                    ).where(
                        ObjectiveRepairExecutionRecord
                        .user_id
                        == user_id
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
                        PlatformEvent.user_id
                        == user_id,
                        PlatformEvent.event_type
                        == OBJECTIVE_REPAIR_PLANNED_EVENT,
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(rows) == 1
        assert len(events) == 1


@pytest.mark.asyncio
async def test_distinct_event_same_semantic_identity_converges():
    user_id = uuid4()

    async with SessionLocal() as db:
        resolution_source = await _source_event(
            db,
            user_id=user_id,
            suffix="resolution",
        )
        resolution = await _resolution_record(
            db,
            user_id=user_id,
            source_event_id=resolution_source.id,
        )
        first_source = await _source_event(
            db,
            user_id=user_id,
            suffix="repair-1",
        )
        second_source = await _source_event(
            db,
            user_id=user_id,
            suffix="repair-2",
        )

        service = ObjectiveRepairExecutionService(
            db
        )

        first = await service.record_plan(
            source_event_id=first_source.id,
            user_id=user_id,
            tenant_id="tenant-1",
            resolution_record_id=resolution.id,
            request=_request(),
            plan=_plan(),
            planner_ref=(
                "customer_support_objective_repair"
            ),
            planner_policy_version=1,
        )

        second = await service.record_plan(
            source_event_id=second_source.id,
            user_id=user_id,
            tenant_id="tenant-1",
            resolution_record_id=resolution.id,
            request=_request(),
            plan=_plan(),
            planner_ref=(
                "customer_support_objective_repair"
            ),
            planner_policy_version=1,
        )

    assert first.created is True
    assert second.created is False
    assert first.record.id == second.record.id
    assert second.event_id is None


@pytest.mark.asyncio
async def test_same_identity_different_plan_conflicts():
    user_id = uuid4()

    async with SessionLocal() as db:
        resolution_source = await _source_event(
            db,
            user_id=user_id,
            suffix="resolution",
        )
        resolution = await _resolution_record(
            db,
            user_id=user_id,
            source_event_id=resolution_source.id,
        )
        first_source = await _source_event(
            db,
            user_id=user_id,
            suffix="repair-1",
        )
        second_source = await _source_event(
            db,
            user_id=user_id,
            suffix="repair-2",
        )

        service = ObjectiveRepairExecutionService(
            db
        )

        await service.record_plan(
            source_event_id=first_source.id,
            user_id=user_id,
            tenant_id="tenant-1",
            resolution_record_id=resolution.id,
            request=_request(),
            plan=_plan(),
            planner_ref=(
                "customer_support_objective_repair"
            ),
            planner_policy_version=1,
        )

        with pytest.raises(
            ObjectiveRepairExecutionConflictError,
            match="different facts",
        ):
            await service.record_plan(
                source_event_id=second_source.id,
                user_id=user_id,
                tenant_id="tenant-1",
                resolution_record_id=resolution.id,
                request=_request(),
                plan=_plan(
                    summary=(
                        "Different persisted plan."
                    )
                ),
                planner_ref=(
                    "customer_support_objective_repair"
                ),
                planner_policy_version=1,
            )


@pytest.mark.asyncio
async def test_attempt_number_is_part_of_identity():
    user_id = uuid4()

    async with SessionLocal() as db:
        resolution_source = await _source_event(
            db,
            user_id=user_id,
            suffix="resolution",
        )
        resolution = await _resolution_record(
            db,
            user_id=user_id,
            source_event_id=resolution_source.id,
        )
        first_source = await _source_event(
            db,
            user_id=user_id,
            suffix="repair-1",
        )
        second_source = await _source_event(
            db,
            user_id=user_id,
            suffix="repair-2",
        )

        service = ObjectiveRepairExecutionService(
            db
        )

        first = await service.record_plan(
            source_event_id=first_source.id,
            user_id=user_id,
            tenant_id="tenant-1",
            resolution_record_id=resolution.id,
            request=_request(),
            plan=_plan(),
            planner_ref=(
                "customer_support_objective_repair"
            ),
            planner_policy_version=1,
            attempt_number=1,
        )

        second = await service.record_plan(
            source_event_id=second_source.id,
            user_id=user_id,
            tenant_id="tenant-1",
            resolution_record_id=resolution.id,
            request=_request(),
            plan=_plan(),
            planner_ref=(
                "customer_support_objective_repair"
            ),
            planner_policy_version=1,
            attempt_number=2,
        )

    assert first.record.id != second.record.id
    assert first.record.attempt_number == 1
    assert second.record.attempt_number == 2


@pytest.mark.asyncio
async def test_repository_get_is_user_scoped():
    first_user = uuid4()
    second_user = uuid4()

    async with SessionLocal() as db:
        resolution_source = await _source_event(
            db,
            user_id=first_user,
            suffix="resolution",
        )
        resolution = await _resolution_record(
            db,
            user_id=first_user,
            source_event_id=resolution_source.id,
        )
        repair_source = await _source_event(
            db,
            user_id=first_user,
            suffix="repair",
        )

        write = await (
            ObjectiveRepairExecutionService(db)
            .record_plan(
                source_event_id=repair_source.id,
                user_id=first_user,
                tenant_id="tenant-1",
                resolution_record_id=resolution.id,
                request=_request(),
                plan=_plan(),
                planner_ref=(
                    "customer_support_objective_repair"
                ),
                planner_policy_version=1,
            )
        )

        repository = (
            ObjectiveRepairExecutionRepository(db)
        )

        own = await repository.get_by_id_for_user(
            user_id=first_user,
            repair_execution_id=write.record.id,
        )
        other = await repository.get_by_id_for_user(
            user_id=second_user,
            repair_execution_id=write.record.id,
        )

    assert own is not None
    assert other is None


@pytest.mark.asyncio
async def test_plan_request_mismatch_is_rejected():
    user_id = uuid4()

    request = _request()
    bad_plan = _plan().model_copy(
        update={
            "repair_request_ref": (
                "objective-repair:other:v1"
            ),
        }
    )

    async with SessionLocal() as db:
        resolution_source = await _source_event(
            db,
            user_id=user_id,
            suffix="resolution",
        )
        resolution = await _resolution_record(
            db,
            user_id=user_id,
            source_event_id=resolution_source.id,
        )
        repair_source = await _source_event(
            db,
            user_id=user_id,
            suffix="repair",
        )

        with pytest.raises(
            ValueError,
            match="request ref does not match",
        ):
            await (
                ObjectiveRepairExecutionService(db)
                .record_plan(
                    source_event_id=repair_source.id,
                    user_id=user_id,
                    tenant_id="tenant-1",
                    resolution_record_id=(
                        resolution.id
                    ),
                    request=request,
                    plan=bad_plan,
                    planner_ref=(
                        "customer_support_"
                        "objective_repair"
                    ),
                    planner_policy_version=1,
                )
            )
