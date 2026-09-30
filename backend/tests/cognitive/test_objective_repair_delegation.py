from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.runtime.objectives.cognition import (
    ObjectiveCognitiveContext,
    ObjectiveCognitiveIdentity,
    ObjectiveCognitiveProvenance,
    ObjectiveCognitiveReference,
    ObjectiveRepairCognitiveFact,
    ObjectiveResolutionCognitiveFact,
)
from app.tcos.cognitive import (
    OBJECTIVE_REPAIR_DELEGATION_EVENT,
    OBJECTIVE_REPAIR_DELEGATION_METRIC_KEY,
    CognitiveRuntime,
    ObjectiveRepairDelegationDecision,
    ObjectiveRepairDelegationKind,
    ObjectiveRepairDelegationReasoner,
    ObjectiveRepairDelegationSafety,
)


NOW = datetime(
    2026,
    8,
    3,
    12,
    0,
    tzinfo=timezone.utc,
)


def _context(
    *,
    present: bool = True,
    terminal: bool = False,
    repair_status: str | None = None,
    repair_attempt: int = 1,
):
    identity = ObjectiveCognitiveIdentity(
        namespace="customer_service.support",
        objective_ref="review-plan-1",
        objective_type="multi_operation",
        objective_version=3,
    )

    if not present:
        return ObjectiveCognitiveContext(
            present=False,
            identity=identity,
            provenance=(
                ObjectiveCognitiveProvenance()
            ),
        )

    resolution_id = uuid4()

    resolution = (
        ObjectiveResolutionCognitiveFact(
            resolution_record_id=resolution_id,
            source_event_id=uuid4(),
            tenant_id="tenant-1",
            workflow_run_id="run-1",
            status=(
                "achieved"
                if terminal
                else "failed"
            ),
            reason_code="test_resolution",
            summary="Test objective resolution.",
            confidence=0.95,
            is_terminal=terminal,
            source_outcome_ref="outcome-1",
            outcome_version=1,
            source_evaluation_ref="evaluation-1",
            evaluation_version=1,
            projection_version=1,
            operation_count=1,
            achieved_operation_count=(
                1 if terminal else 0
            ),
            unresolved_operation_count=(
                0 if terminal else 1
            ),
            failed_operation_count=(
                0 if terminal else 1
            ),
            pending_operation_count=0,
            unknown_operation_count=0,
            not_executed_operation_count=0,
            unresolved_operation_refs=(
                ()
                if terminal
                else ("support-operation:refund",)
            ),
            failed_operation_refs=(
                ()
                if terminal
                else ("support-operation:refund",)
            ),
            created_at=NOW,
        )
    )

    repair = None

    if repair_status is not None:
        repair = ObjectiveRepairCognitiveFact(
            repair_execution_id=uuid4(),
            resolution_record_id=resolution_id,
            source_event_id=uuid4(),
            status=repair_status,
            attempt_number=repair_attempt,
            repair_request_ref="repair-request-1",
            repair_request_version=1,
            planner_ref=(
                "customer_support_objective_repair"
            ),
            planner_policy_version=1,
            disposition="replan_remaining",
            reason_code="test_repair",
            summary="Test repair attempt.",
            confidence=0.9,
            automatic_execution_allowed=False,
            human_approval_required=True,
            workflow_run_id="repair-run-1",
            runtime_status="ok",
            repair_result_status=repair_status,
            created_at=NOW,
            completed_at=(
                NOW
                if repair_status
                in {
                    "completed",
                    "failed",
                    "rejected",
                }
                else None
            ),
        )

    return ObjectiveCognitiveContext(
        present=True,
        identity=identity,
        resolution=resolution,
        latest_repair=repair,
        provenance=ObjectiveCognitiveProvenance(
            resolution_record_id=resolution_id,
            repair_execution_id=(
                repair.repair_execution_id
                if repair is not None
                else None
            ),
        ),
    )


def test_no_context_does_not_delegate():
    decision = (
        ObjectiveRepairDelegationReasoner()
        .reason(None)
    )

    assert decision.kind == (
        ObjectiveRepairDelegationKind
        .NO_DELEGATION
    )
    assert decision.requested is False
    assert (
        decision.safety
        .product_planning_required
        is False
    )


def test_absent_objective_does_not_delegate():
    decision = (
        ObjectiveRepairDelegationReasoner()
        .reason(_context(present=False))
    )

    assert decision.kind == (
        ObjectiveRepairDelegationKind
        .NO_DELEGATION
    )
    assert decision.requested is False


def test_resolved_objective_does_not_delegate():
    decision = (
        ObjectiveRepairDelegationReasoner()
        .reason(_context(terminal=True))
    )

    assert decision.kind == (
        ObjectiveRepairDelegationKind
        .NO_DELEGATION
    )
    assert decision.requested is False


def test_unresolved_objective_requests_first_attempt():
    context = _context()

    decision = (
        ObjectiveRepairDelegationReasoner()
        .reason(context)
    )

    assert decision.kind == (
        ObjectiveRepairDelegationKind
        .REPAIR_PLANNING_REQUESTED
    )
    assert decision.requested is True
    assert decision.requested_attempt_number == 1
    assert decision.current_attempt_number is None

    assert decision.objective_namespace == (
        "customer_service.support"
    )
    assert decision.objective_type == (
        "multi_operation"
    )
    assert decision.objective_ref == (
        "review-plan-1"
    )
    assert decision.objective_version == 3

    assert decision.resolution_record_id == (
        context.resolution.resolution_record_id
    )


@pytest.mark.parametrize(
    "repair_status",
    [
        "planned",
        "queued",
        "running",
        "paused",
    ],
)
def test_active_repair_is_observed_not_duplicated(
    repair_status,
):
    context = _context(
        repair_status=repair_status,
        repair_attempt=2,
    )

    decision = (
        ObjectiveRepairDelegationReasoner()
        .reason(context)
    )

    assert decision.kind == (
        ObjectiveRepairDelegationKind
        .OBSERVE_EXISTING_REPAIR
    )
    assert decision.requested is False
    assert decision.current_attempt_number == 2
    assert decision.requested_attempt_number is None
    assert decision.repair_execution_id == (
        context.latest_repair.repair_execution_id
    )


@pytest.mark.parametrize(
    "repair_status",
    [
        "completed",
        "failed",
        "rejected",
    ],
)
def test_terminal_repair_requests_next_attempt(
    repair_status,
):
    context = _context(
        repair_status=repair_status,
        repair_attempt=3,
    )

    decision = (
        ObjectiveRepairDelegationReasoner()
        .reason(context)
    )

    assert decision.kind == (
        ObjectiveRepairDelegationKind
        .SUBSEQUENT_REPAIR_PLANNING_REQUESTED
    )
    assert decision.requested is True
    assert decision.current_attempt_number == 3
    assert decision.requested_attempt_number == 4


def test_decision_safety_is_non_authorizing():
    decision = (
        ObjectiveRepairDelegationReasoner()
        .reason(_context())
    )

    assert decision.safety.informational_only is True
    assert (
        decision.safety
        .product_planning_required
        is True
    )

    assert decision.safety.persists_repair is False
    assert decision.safety.publishes_event is False
    assert decision.safety.enqueues_job is False
    assert decision.safety.launches_workflow is False
    assert (
        decision.safety.authorizes_execution
        is False
    )

    assert (
        decision.safety
        .bypasses_product_registry
        is False
    )
    assert (
        decision.safety
        .bypasses_canonical_source_loading
        is False
    )
    assert (
        decision.safety
        .bypasses_idempotency
        is False
    )
    assert (
        decision.safety.bypasses_approval
        is False
    )
    assert (
        decision.safety
        .bypasses_verification
        is False
    )


def test_contract_rejects_side_effect_flags():
    state = (
        ObjectiveRepairDelegationReasoner()
        .reason(None)
        .objective_state
    )

    with pytest.raises(ValidationError):
        ObjectiveRepairDelegationDecision(
            kind=(
                ObjectiveRepairDelegationKind
                .NO_DELEGATION
            ),
            requested=False,
            objective_state=state,
            reason_code="invalid",
            summary="Invalid decision.",
            safety=ObjectiveRepairDelegationSafety(
                persists_repair=True
            ),
        )


def test_decision_is_immutable():
    decision = (
        ObjectiveRepairDelegationReasoner()
        .reason(None)
    )

    with pytest.raises(ValidationError):
        decision.requested = True


@pytest.mark.asyncio
async def test_runtime_projects_explicit_objective_decision(
    monkeypatch,
):
    from app.runtime.objectives.cognition import (
        ObjectiveCognitiveContextLoader,
    )

    context = _context()

    load = AsyncMock(
        return_value=context
    )

    monkeypatch.setattr(
        ObjectiveCognitiveContextLoader,
        "load_for_objective",
        load,
    )

    runtime = CognitiveRuntime()

    session = await runtime.execute_goal_runtime(
        goal="Reply to customer",
        ctx=SimpleNamespace(
            db=object(),
            user_id=uuid4(),
        ),
        objective=ObjectiveCognitiveReference(
            namespace="customer_service.support",
            objective_ref="review-plan-1",
        ),
    )

    delegation = session.metrics[
        OBJECTIVE_REPAIR_DELEGATION_METRIC_KEY
    ]

    assert delegation["kind"] == (
        "repair_planning_requested"
    )
    assert delegation["requested"] is True
    assert delegation[
        "requested_attempt_number"
    ] == 1

    events = [
        event
        for event in session.events
        if event.type
        == OBJECTIVE_REPAIR_DELEGATION_EVENT
    ]

    assert len(events) == 1
    assert events[0].payload["requested"] is True
    assert (
        session.metrics["cognitive_event_count"]
        == len(session.events)
    )


@pytest.mark.asyncio
async def test_runtime_does_not_project_without_reference():
    session = await CognitiveRuntime().execute_goal_runtime(
        goal="Reply to customer",
        ctx=object(),
    )

    assert (
        OBJECTIVE_REPAIR_DELEGATION_METRIC_KEY
        not in session.metrics
    )

    assert all(
        event.type
        != OBJECTIVE_REPAIR_DELEGATION_EVENT
        for event in session.events
    )


def test_synchronous_runtime_remains_delegation_free():
    session = CognitiveRuntime().execute_goal(
        goal="Reply to customer"
    )

    assert (
        OBJECTIVE_REPAIR_DELEGATION_METRIC_KEY
        not in session.metrics
    )

    assert all(
        event.type
        != OBJECTIVE_REPAIR_DELEGATION_EVENT
        for event in session.events
    )
