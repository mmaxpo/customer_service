import pytest

from app.agents_runtime.state import (
    AgentState,
    AgentStatus,
    InvalidAgentStateTransition,
    PendingApproval,
)


def test_initial_state_is_created():
    state = AgentState()

    assert state.status == AgentStatus.CREATED
    assert state.steps == 0
    assert state.final_output is None


def test_mark_running():
    state = AgentState()

    state.mark_running()

    assert state.status == AgentStatus.RUNNING


def test_mark_completed():
    state = AgentState()
    state.mark_running()

    state.mark_completed("done")

    assert state.status == AgentStatus.COMPLETED
    assert state.final_output == "done"


def test_invalid_transition_from_completed_to_running():
    state = AgentState()
    state.mark_running()
    state.mark_completed("done")

    with pytest.raises(InvalidAgentStateTransition):
        state.mark_running()


def test_mark_paused_with_pending_approval():
    state = AgentState()
    state.mark_running()

    approval = PendingApproval(
        tool_name="dangerous_test_action",
        arguments={"resource_id": "ORD-1", "amount": 10.0},
        call_id="call_123",
    )

    state.mark_paused(approval)

    assert state.status == AgentStatus.PAUSED
    assert state.pending_approval.tool_name == "dangerous_test_action"


def test_resume_from_pause():
    state = AgentState()
    state.mark_running()

    state.mark_paused(
        PendingApproval(
            tool_name="dangerous_test_action",
            arguments={"resource_id": "ORD-1", "amount": 10.0},
        )
    )

    state.resume_from_pause()

    assert state.status == AgentStatus.RUNNING
    assert state.pending_approval is None


def test_mark_failed_records_error():
    state = AgentState()
    state.mark_running()
    state.steps = 3

    state.mark_failed("bad thing")

    assert state.status == AgentStatus.FAILED
    assert state.errors[0].step == 3
    assert state.errors[0].message == "bad thing"
