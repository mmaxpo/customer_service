from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.runtime.objectives.cognition import (
    ObjectiveCognitiveContext,
    ObjectiveCognitiveIdentity,
    ObjectiveCognitiveProvenance,
    ObjectiveRepairCognitiveFact,
    ObjectiveResolutionCognitiveFact,
)
from app.tcos.planner.runtime.objective_state_reasoner import (
    ObjectivePlanningStateKind,
    ObjectivePlanningStateReasoner,
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
    resolution_status: str = "failed",
    unresolved_count: int = 1,
    repair_status: str | None = None,
    repair_disposition: str = "replan_remaining",
    human_approval_required: bool = True,
    automatic_execution_allowed: bool = False,
) -> ObjectiveCognitiveContext:
    identity = ObjectiveCognitiveIdentity(
        namespace="customer_service.support",
        objective_ref="review-plan-1",
        objective_type="multi_operation",
        objective_version=1,
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
            workflow_run_id="workflow-run-1",
            status=resolution_status,
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
                0 if terminal else unresolved_count
            ),
            failed_operation_count=(
                0 if terminal else unresolved_count
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
            attempt_number=2,
            repair_request_ref="repair-request-1",
            repair_request_version=1,
            planner_ref=(
                "customer_support_objective_repair"
            ),
            planner_policy_version=1,
            disposition=repair_disposition,
            reason_code="test_repair",
            summary="Test repair attempt.",
            confidence=0.90,
            automatic_execution_allowed=(
                automatic_execution_allowed
            ),
            human_approval_required=(
                human_approval_required
            ),
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


def test_no_context_is_classified():
    result = (
        ObjectivePlanningStateReasoner()
        .reason(None)
    )

    assert result.kind == (
        ObjectivePlanningStateKind.NO_CONTEXT
    )
    assert result.objective_present is False
    assert result.repair_present is False


def test_absent_context_is_classified():
    result = (
        ObjectivePlanningStateReasoner()
        .reason(_context(present=False))
    )

    assert result.kind == (
        ObjectivePlanningStateKind.ABSENT
    )
    assert result.objective_present is False
    assert result.unresolved_operation_count == 0


def test_terminal_objective_is_resolved():
    result = (
        ObjectivePlanningStateReasoner()
        .reason(
            _context(
                terminal=True,
                resolution_status="achieved",
            )
        )
    )

    assert result.kind == (
        ObjectivePlanningStateKind.RESOLVED
    )
    assert result.objective_terminal is True
    assert result.unresolved_operation_count == 0


@pytest.mark.parametrize(
    "repair_status",
    [
        "planned",
        "queued",
        "running",
        "paused",
    ],
)
def test_active_repair_statuses_are_classified(
    repair_status,
):
    result = (
        ObjectivePlanningStateReasoner()
        .reason(
            _context(
                repair_status=repair_status
            )
        )
    )

    assert result.kind == (
        ObjectivePlanningStateKind.REPAIR_ACTIVE
    )
    assert result.repair_present is True
    assert result.repair_terminal is False
    assert result.repair_status == repair_status


@pytest.mark.parametrize(
    "repair_status",
    [
        "completed",
        "failed",
        "rejected",
    ],
)
def test_terminal_repair_statuses_are_classified(
    repair_status,
):
    result = (
        ObjectivePlanningStateReasoner()
        .reason(
            _context(
                repair_status=repair_status
            )
        )
    )

    assert result.kind == (
        ObjectivePlanningStateKind
        .REPAIR_TERMINAL
    )
    assert result.objective_terminal is False
    assert result.repair_terminal is True
    assert result.repair_status == repair_status


def test_unresolved_without_repair_is_classified():
    result = (
        ObjectivePlanningStateReasoner()
        .reason(_context())
    )

    assert result.kind == (
        ObjectivePlanningStateKind.UNRESOLVED
    )
    assert result.unresolved_operation_count == 1
    assert result.unresolved_operation_refs == (
        "support-operation:refund",
    )


def test_preserves_repair_safety_facts_without_authorizing():
    result = (
        ObjectivePlanningStateReasoner()
        .reason(
            _context(
                repair_status="paused",
                human_approval_required=True,
                automatic_execution_allowed=False,
            )
        )
    )

    assert result.human_approval_required is True
    assert (
        result.automatic_execution_allowed
        is False
    )

    assert result.safety.informational_only is True
    assert result.safety.affects_ranking is False
    assert (
        result.safety
        .affects_capability_selection
        is False
    )
    assert (
        result.safety.authorizes_execution
        is False
    )
    assert result.safety.launches_repair is False
    assert (
        result.safety.bypasses_approval
        is False
    )
    assert (
        result.safety.bypasses_verification
        is False
    )


def test_result_is_immutable():
    result = (
        ObjectivePlanningStateReasoner()
        .reason(_context())
    )

    with pytest.raises(ValidationError):
        result.kind = (
            ObjectivePlanningStateKind.RESOLVED
        )


def test_reasoner_does_not_mutate_context():
    context = _context(
        repair_status="rejected"
    )
    before = context.model_dump(
        mode="python"
    )

    ObjectivePlanningStateReasoner().reason(
        context
    )

    assert context.model_dump(
        mode="python"
    ) == before


def test_unknown_repair_status_does_not_claim_active_or_terminal():
    result = (
        ObjectivePlanningStateReasoner()
        .reason(
            _context(
                repair_status="unknown_status"
            )
        )
    )

    assert result.kind == (
        ObjectivePlanningStateKind.UNRESOLVED
    )
    assert result.repair_present is True
    assert result.repair_terminal is False
