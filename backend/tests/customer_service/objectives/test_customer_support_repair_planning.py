from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.domains.customer_service.services.support.repair.planning import (
    CUSTOMER_SUPPORT_REPAIR_PLANNER_REF,
    OBJECTIVE_REPAIR_PLANNING_REQUESTED_EVENT,
    CustomerSupportRepairPlanningAttemptError,
    CustomerSupportRepairPlanningCoordinator,
    CustomerSupportRepairPlanningIdentityError,
    CustomerSupportRepairPlanningNotFoundError,
)
from app.runtime.objectives.repair import (
    ObjectiveRepairDisposition,
)
from app.tcos.cognitive import (
    ObjectiveRepairDelegationKind,
)


def _safety():
    return SimpleNamespace(
        product_planning_required=True,
        persists_repair=False,
        publishes_event=False,
        enqueues_job=False,
        launches_workflow=False,
        authorizes_execution=False,
        bypasses_product_registry=False,
        bypasses_canonical_source_loading=False,
        bypasses_idempotency=False,
        bypasses_approval=False,
        bypasses_verification=False,
    )


def _decision(
    *,
    kind=(
        ObjectiveRepairDelegationKind
        .REPAIR_PLANNING_REQUESTED
    ),
    requested_attempt_number=1,
    current_attempt_number=None,
    repair_execution_id=None,
    resolution_record_id=None,
):
    return SimpleNamespace(
        schema_version="objective_repair_delegation.v1",
        kind=kind,
        requested=True,
        objective_namespace="customer_service.support",
        objective_type="multi_operation",
        objective_ref="review-plan-1",
        objective_version=1,
        resolution_record_id=(
            resolution_record_id or uuid4()
        ),
        repair_execution_id=repair_execution_id,
        current_attempt_number=current_attempt_number,
        requested_attempt_number=(
            requested_attempt_number
        ),
        reason_code=(
            "objective_unresolved_without_repair"
        ),
        safety=_safety(),
    )


def _resolution(
    *,
    resolution_record_id,
    tenant_id="tenant-1",
):
    return SimpleNamespace(
        id=resolution_record_id,
        user_id=uuid4(),
        tenant_id=tenant_id,
        objective_namespace="customer_service.support",
        objective_type="multi_operation",
        objective_ref="review-plan-1",
        objective_version=1,
        projection_version=1,
    )


def _canonical(*, resolution_record_id):
    review_plan = SimpleNamespace(
        operations=(SimpleNamespace(),),
        model_dump=Mock(
            return_value={
                "version": 1,
                "operations": [{}],
            }
        ),
    )

    return SimpleNamespace(
        review_plan_id="review-plan-1",
        review_plan=review_plan,
        support_outcome_id=uuid4(),
        workflow_run_id=uuid4(),
        resolution_record_id=resolution_record_id,
    )


def _coordinator(
    *,
    resolution,
    latest=None,
):
    db = SimpleNamespace(
        commit=AsyncMock(),
        refresh=AsyncMock(),
        flush=AsyncMock(),
        rollback=AsyncMock(),
    )

    assessment = SimpleNamespace()

    resolutions = SimpleNamespace(
        get_for_user=AsyncMock(
            return_value=resolution
        ),
        assessment_from_record=Mock(
            return_value=assessment
        ),
    )

    repairs = SimpleNamespace(
        get_latest_for_resolution=AsyncMock(
            return_value=latest
        )
    )

    canonical = _canonical(
        resolution_record_id=resolution.id
    )

    review_plans = SimpleNamespace(
        load_for_resolution=AsyncMock(
            return_value=canonical
        )
    )

    request = SimpleNamespace(
        source=SimpleNamespace(
            objective=SimpleNamespace()
        )
    )

    request_builder = SimpleNamespace(
        build=Mock(return_value=request)
    )

    plan = SimpleNamespace()

    planner = SimpleNamespace(
        plan_repair=Mock(return_value=plan)
    )

    registry = SimpleNamespace(
        resolve=Mock(return_value=planner)
    )

    command_event = SimpleNamespace(id=uuid4())

    events = SimpleNamespace(
        append=AsyncMock(
            return_value=command_event
        )
    )

    record = SimpleNamespace(id=uuid4())

    write = SimpleNamespace(
        record=record,
        created=True,
        event_id=uuid4(),
    )

    repair_service = SimpleNamespace(
        record_plan=AsyncMock(
            return_value=write
        )
    )

    coordinator = (
        CustomerSupportRepairPlanningCoordinator(
            db,
            resolutions=resolutions,
            repairs=repairs,
            review_plans=review_plans,
            registry=registry,
            request_builder=request_builder,
            repair_service=repair_service,
            events=events,
        )
    )

    return SimpleNamespace(
        coordinator=coordinator,
        db=db,
        resolutions=resolutions,
        repairs=repairs,
        review_plans=review_plans,
        request_builder=request_builder,
        registry=registry,
        planner=planner,
        events=events,
        repair_service=repair_service,
        assessment=assessment,
        canonical=canonical,
        request=request,
        plan=plan,
        write=write,
        command_event=command_event,
    )


@pytest.mark.asyncio
async def test_requested_delegation_records_plan_atomically():
    user_id = uuid4()
    resolution_record_id = uuid4()

    decision = _decision(
        resolution_record_id=resolution_record_id
    )
    resolution = _resolution(
        resolution_record_id=resolution_record_id
    )
    deps = _coordinator(
        resolution=resolution
    )

    result = await deps.coordinator.plan(
        decision=decision,
        user_id=user_id,
        tenant_id="tenant-1",
    )

    deps.resolutions.get_for_user.assert_awaited_once_with(
        user_id=user_id,
        record_id=resolution_record_id,
    )

    deps.review_plans.load_for_resolution.assert_awaited_once_with(
        user_id=user_id,
        resolution_record_id=resolution_record_id,
    )

    deps.registry.resolve.assert_called_once_with(
        namespace="customer_service.support",
        objective_type="multi_operation",
    )

    deps.events.append.assert_awaited_once()

    event_call = deps.events.append.await_args.kwargs

    assert event_call["event_type"] == (
        OBJECTIVE_REPAIR_PLANNING_REQUESTED_EVENT
    )
    assert event_call["commit"] is False
    assert event_call["payload"][
        "requested_attempt_number"
    ] == 1

    deps.repair_service.record_plan.assert_awaited_once()

    write_call = (
        deps.repair_service
        .record_plan
        .await_args
        .kwargs
    )

    assert write_call["source_event_id"] == (
        deps.command_event.id
    )
    assert write_call["planner_ref"] == (
        CUSTOMER_SUPPORT_REPAIR_PLANNER_REF
    )
    assert write_call["attempt_number"] == 1
    assert write_call["commit"] is False

    deps.db.commit.assert_awaited_once()
    deps.db.refresh.assert_awaited_once_with(
        deps.write.record
    )

    assert result.command_event_id == (
        deps.command_event.id
    )
    assert result.write is deps.write


@pytest.mark.asyncio
async def test_commit_false_flushes_without_committing():
    resolution_record_id = uuid4()
    decision = _decision(
        resolution_record_id=resolution_record_id
    )
    deps = _coordinator(
        resolution=_resolution(
            resolution_record_id=(
                resolution_record_id
            )
        )
    )

    await deps.coordinator.plan(
        decision=decision,
        user_id=uuid4(),
        tenant_id="tenant-1",
        commit=False,
    )

    deps.db.commit.assert_not_awaited()
    deps.db.refresh.assert_not_awaited()
    deps.db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_non_planning_delegation_is_rejected():
    resolution_record_id = uuid4()
    decision = _decision(
        resolution_record_id=resolution_record_id
    )
    decision.kind = (
        ObjectiveRepairDelegationKind
        .OBSERVE_EXISTING_REPAIR
    )
    decision.requested = False
    decision.safety.product_planning_required = False

    deps = _coordinator(
        resolution=_resolution(
            resolution_record_id=(
                resolution_record_id
            )
        )
    )

    with pytest.raises(
        CustomerSupportRepairPlanningIdentityError,
        match="planning-request delegation",
    ):
        await deps.coordinator.plan(
            decision=decision,
            user_id=uuid4(),
            tenant_id="tenant-1",
        )

    deps.resolutions.get_for_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_cross_user_resolution_is_not_found():
    resolution_record_id = uuid4()
    decision = _decision(
        resolution_record_id=resolution_record_id
    )

    deps = _coordinator(
        resolution=_resolution(
            resolution_record_id=(
                resolution_record_id
            )
        )
    )

    deps.resolutions.get_for_user.return_value = None

    with pytest.raises(
        CustomerSupportRepairPlanningNotFoundError,
        match="not found for user",
    ):
        await deps.coordinator.plan(
            decision=decision,
            user_id=uuid4(),
            tenant_id="tenant-1",
        )

    deps.events.append.assert_not_awaited()


@pytest.mark.asyncio
async def test_tenant_mismatch_is_rejected():
    resolution_record_id = uuid4()
    decision = _decision(
        resolution_record_id=resolution_record_id
    )

    deps = _coordinator(
        resolution=_resolution(
            resolution_record_id=(
                resolution_record_id
            ),
            tenant_id="other-tenant",
        )
    )

    with pytest.raises(
        CustomerSupportRepairPlanningIdentityError,
        match="tenant",
    ):
        await deps.coordinator.plan(
            decision=decision,
            user_id=uuid4(),
            tenant_id="tenant-1",
        )

    deps.review_plans.load_for_resolution.assert_not_awaited()
    deps.events.append.assert_not_awaited()


@pytest.mark.asyncio
async def test_subsequent_attempt_requires_terminal_latest():
    resolution_record_id = uuid4()
    repair_execution_id = uuid4()

    decision = _decision(
        kind=(
            ObjectiveRepairDelegationKind
            .SUBSEQUENT_REPAIR_PLANNING_REQUESTED
        ),
        requested_attempt_number=2,
        current_attempt_number=1,
        repair_execution_id=repair_execution_id,
        resolution_record_id=resolution_record_id,
    )

    latest = SimpleNamespace(
        id=repair_execution_id,
        attempt_number=1,
        status="running",
        plan_json={},
    )

    deps = _coordinator(
        resolution=_resolution(
            resolution_record_id=(
                resolution_record_id
            )
        ),
        latest=latest,
    )

    with pytest.raises(
        CustomerSupportRepairPlanningAttemptError,
        match="terminal",
    ):
        await deps.coordinator.plan(
            decision=decision,
            user_id=uuid4(),
            tenant_id="tenant-1",
        )

    deps.events.append.assert_not_awaited()


@pytest.mark.asyncio
async def test_same_attempt_retry_is_allowed():
    resolution_record_id = uuid4()
    existing_plan = {
        "schema_version": "objective_repair_plan.v1"
    }

    latest = SimpleNamespace(
        id=uuid4(),
        attempt_number=1,
        status="planned",
        plan_json=existing_plan,
    )

    decision = _decision(
        resolution_record_id=resolution_record_id,
        requested_attempt_number=1,
    )

    deps = _coordinator(
        resolution=_resolution(
            resolution_record_id=(
                resolution_record_id
            )
        ),
        latest=latest,
    )

    parsed_plan = SimpleNamespace()
    model_validate = Mock(
        return_value=parsed_plan
    )

    from app.domains.customer_service.services.support.repair import (
        planning as module,
    )

    original = (
        module.ObjectiveRepairPlan.model_validate
    )
    module.ObjectiveRepairPlan.model_validate = (
        model_validate
    )

    try:
        await deps.coordinator.plan(
            decision=decision,
            user_id=uuid4(),
            tenant_id="tenant-1",
        )
    finally:
        module.ObjectiveRepairPlan.model_validate = (
            original
        )

    planning_context = (
        deps.planner.plan_repair.call_args.args[0]
    )

    assert planning_context.prior_repair_plans == (
        parsed_plan,
    )


def test_constraints_never_allow_automatic_execution():
    resolution_record_id = uuid4()
    canonical = _canonical(
        resolution_record_id=resolution_record_id
    )

    constraints = (
        CustomerSupportRepairPlanningCoordinator
        ._constraints(
            requested_attempt_number=1,
            canonical=canonical,
        )
    )

    assert constraints.allow_automatic_execution is False
    assert constraints.metadata[
        "automatic_mutation_allowed"
    ] is False
    assert constraints.metadata[
        "fresh_approval_required_for_mutation"
    ] is True

    assert set(constraints.allowed_dispositions) == {
        ObjectiveRepairDisposition.RETRY_OPERATION,
        ObjectiveRepairDisposition.WAIT_FOR_RESULT,
        ObjectiveRepairDisposition.REPLAN_REMAINING,
        ObjectiveRepairDisposition.REQUEST_HUMAN_ACTION,
        ObjectiveRepairDisposition.STOP_REPAIR,
    }
