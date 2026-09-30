from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.models.models import (
    ObjectiveResolutionRecord,
    PlatformEvent,
)
from app.platform.events.event_store import (
    PlatformEventStore,
)
from app.runtime.objectives.resolution import (
    OBJECTIVE_RESOLUTION_ASSESSED_EVENT,
    ObjectiveOperationResolution,
    ObjectiveOperationStatus,
    ObjectiveReference,
    ObjectiveResolutionAssessment,
    ObjectiveResolutionConflictError,
    ObjectiveResolutionRepository,
    ObjectiveResolutionService,
    ObjectiveResolutionSource,
    ObjectiveResolutionStatus,
)


def _assessment(
    *,
    evaluation_ref: str,
    objective_ref: str = "objective-1",
    status=(
        ObjectiveResolutionStatus
        .PARTIALLY_ACHIEVED
    ),
    summary: str = "Partially achieved.",
    evaluation_version: int = 1,
    outcome_version: int = 1,
):
    operations = (
        ObjectiveOperationResolution(
            operation_ref="operation-1",
            operation_type="refund",
            status=(
                ObjectiveOperationStatus.ACHIEVED
            ),
        ),
        ObjectiveOperationResolution(
            operation_ref="operation-2",
            operation_type="replacement",
            status=(
                ObjectiveOperationStatus.PENDING
            ),
        ),
    )

    if status == ObjectiveResolutionStatus.ACHIEVED:
        operations = (
            ObjectiveOperationResolution(
                operation_ref="operation-1",
                operation_type="refund",
                status=(
                    ObjectiveOperationStatus.ACHIEVED
                ),
            ),
        )

    return ObjectiveResolutionAssessment(
        objective=ObjectiveReference(
            namespace="example.support",
            objective_type="multi_operation",
            objective_ref=objective_ref,
            objective_version=1,
        ),
        source=ObjectiveResolutionSource(
            outcome_ref="outcome-1",
            outcome_version=outcome_version,
            evaluation_ref=evaluation_ref,
            evaluation_version=evaluation_version,
            workflow_run_id="run-1",
        ),
        status=status,
        reason_code="test_resolution",
        summary=summary,
        confidence=0.9,
        is_terminal=(
            status
            == ObjectiveResolutionStatus.ACHIEVED
        ),
        operations=operations,
        metadata={
            "safe": True,
        },
    )


async def _source_event(
    db,
    *,
    user_id,
):
    return await PlatformEventStore(db).append(
        user_id=user_id,
        event_type=(
            "example.objective.evaluated"
        ),
        source="test",
        payload={},
        meta={},
        commit=True,
    )


@pytest.mark.asyncio
async def test_repository_records_and_round_trips():
    user_id = uuid4()

    async with SessionLocal() as db:
        event = await _source_event(
            db,
            user_id=user_id,
        )
        repository = (
            ObjectiveResolutionRepository(db)
        )
        assessment = _assessment(
            evaluation_ref=str(uuid4())
        )

        row, created = await repository.record(
            source_event_id=event.id,
            user_id=user_id,
            tenant_id="tenant-1",
            assessment=assessment,
            commit=True,
        )

        restored = (
            repository.assessment_from_record(
                row
            )
        )

    assert created is True
    assert restored == assessment
    assert row.operation_count == 2
    assert row.achieved_operation_count == 1
    assert row.unresolved_operation_count == 1
    assert row.pending_operation_count == 1


@pytest.mark.asyncio
async def test_duplicate_source_event_is_idempotent():
    user_id = uuid4()

    async with SessionLocal() as db:
        event = await _source_event(
            db,
            user_id=user_id,
        )
        repository = (
            ObjectiveResolutionRepository(db)
        )
        assessment = _assessment(
            evaluation_ref=str(uuid4())
        )

        first, first_created = (
            await repository.record(
                source_event_id=event.id,
                user_id=user_id,
                tenant_id=None,
                assessment=assessment,
                commit=True,
            )
        )
        second, second_created = (
            await repository.record(
                source_event_id=event.id,
                user_id=user_id,
                tenant_id=None,
                assessment=assessment,
                commit=True,
            )
        )

    assert first_created is True
    assert second_created is False
    assert first.id == second.id


@pytest.mark.asyncio
async def test_duplicate_evaluation_via_new_event_is_idempotent():
    user_id = uuid4()
    evaluation_ref = str(uuid4())

    async with SessionLocal() as db:
        first_event = await _source_event(
            db,
            user_id=user_id,
        )
        second_event = await _source_event(
            db,
            user_id=user_id,
        )

        repository = (
            ObjectiveResolutionRepository(db)
        )
        assessment = _assessment(
            evaluation_ref=evaluation_ref
        )

        first, first_created = (
            await repository.record(
                source_event_id=first_event.id,
                user_id=user_id,
                tenant_id=None,
                assessment=assessment,
                commit=True,
            )
        )
        second, second_created = (
            await repository.record(
                source_event_id=second_event.id,
                user_id=user_id,
                tenant_id=None,
                assessment=assessment,
                commit=True,
            )
        )

    assert first_created is True
    assert second_created is False
    assert first.id == second.id


@pytest.mark.asyncio
async def test_same_source_with_changed_facts_conflicts():
    user_id = uuid4()
    evaluation_ref = str(uuid4())

    async with SessionLocal() as db:
        event = await _source_event(
            db,
            user_id=user_id,
        )

        repository = (
            ObjectiveResolutionRepository(db)
        )

        await repository.record(
            source_event_id=event.id,
            user_id=user_id,
            tenant_id=None,
            assessment=_assessment(
                evaluation_ref=evaluation_ref,
                summary="Original summary.",
            ),
            commit=True,
        )

        with pytest.raises(
            ObjectiveResolutionConflictError,
            match="different assessment facts",
        ):
            await repository.record(
                source_event_id=event.id,
                user_id=user_id,
                tenant_id=None,
                assessment=_assessment(
                    evaluation_ref=evaluation_ref,
                    summary="Changed summary.",
                ),
                commit=True,
            )


@pytest.mark.asyncio
async def test_new_projection_version_creates_new_record():
    user_id = uuid4()
    evaluation_ref = str(uuid4())

    async with SessionLocal() as db:
        first_event = await _source_event(
            db,
            user_id=user_id,
        )
        second_event = await _source_event(
            db,
            user_id=user_id,
        )
        repository = (
            ObjectiveResolutionRepository(db)
        )
        assessment = _assessment(
            evaluation_ref=evaluation_ref
        )

        first, _ = await repository.record(
            source_event_id=first_event.id,
            user_id=user_id,
            tenant_id=None,
            assessment=assessment,
            projection_version=1,
            commit=True,
        )
        second, created = await repository.record(
            source_event_id=second_event.id,
            user_id=user_id,
            tenant_id=None,
            assessment=assessment,
            projection_version=2,
            commit=True,
        )

    assert created is True
    assert first.id != second.id
    assert second.projection_version == 2


@pytest.mark.asyncio
async def test_latest_is_user_scoped_and_version_ordered():
    owner_id = uuid4()
    other_id = uuid4()
    objective_ref = str(uuid4())

    async with SessionLocal() as db:
        repository = (
            ObjectiveResolutionRepository(db)
        )

        first_event = await _source_event(
            db,
            user_id=owner_id,
        )
        second_event = await _source_event(
            db,
            user_id=owner_id,
        )
        other_event = await _source_event(
            db,
            user_id=other_id,
        )

        first, _ = await repository.record(
            source_event_id=first_event.id,
            user_id=owner_id,
            tenant_id=None,
            assessment=_assessment(
                evaluation_ref=str(uuid4()),
                objective_ref=objective_ref,
                evaluation_version=1,
            ),
            commit=True,
        )

        second, _ = await repository.record(
            source_event_id=second_event.id,
            user_id=owner_id,
            tenant_id=None,
            assessment=_assessment(
                evaluation_ref=str(uuid4()),
                objective_ref=objective_ref,
                evaluation_version=2,
            ),
            commit=True,
        )

        await repository.record(
            source_event_id=other_event.id,
            user_id=other_id,
            tenant_id=None,
            assessment=_assessment(
                evaluation_ref=str(uuid4()),
                objective_ref=objective_ref,
                evaluation_version=99,
            ),
            commit=True,
        )

        latest = await (
            repository.get_latest_for_objective(
                user_id=owner_id,
                objective_namespace=(
                    "example.support"
                ),
                objective_ref=objective_ref,
            )
        )

        hidden = await repository.get_for_user(
            user_id=other_id,
            record_id=first.id,
        )

    assert latest is not None
    assert latest.id == second.id
    assert hidden is None


@pytest.mark.asyncio
async def test_service_emits_one_minimal_event():
    user_id = uuid4()

    async with SessionLocal() as db:
        source_event = await _source_event(
            db,
            user_id=user_id,
        )

        service = ObjectiveResolutionService(db)
        assessment = _assessment(
            evaluation_ref=str(uuid4())
        )

        first = await service.record_assessment(
            source_event_id=source_event.id,
            user_id=user_id,
            tenant_id="tenant-1",
            assessment=assessment,
        )
        second = await service.record_assessment(
            source_event_id=source_event.id,
            user_id=user_id,
            tenant_id="tenant-1",
            assessment=assessment,
        )

    assert first.created is True
    assert first.event_id is not None
    assert second.created is False
    assert second.event_id is None
    assert first.record.id == second.record.id

    async with SessionLocal() as db:
        events = list(
            (
                await db.execute(
                    select(PlatformEvent).where(
                        PlatformEvent.user_id
                        == user_id,
                        PlatformEvent.event_type
                        == (
                            OBJECTIVE_RESOLUTION_ASSESSED_EVENT
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )

        rows = list(
            (
                await db.execute(
                    select(
                        ObjectiveResolutionRecord
                    ).where(
                        ObjectiveResolutionRecord
                        .user_id
                        == user_id
                    )
                )
            )
            .scalars()
            .all()
        )

    assert len(rows) == 1
    assert len(events) == 1

    payload = dict(events[0].payload or {})
    serialized_payload = str(payload)

    assert payload["resolution_record_id"] == (
        str(first.record.id)
    )
    assert payload[
        "unresolved_operation_count"
    ] == 1
    assert "assessment_json" not in payload
    assert "safe" not in serialized_payload
