import pytest

from app.agents_runtime.state import (
    AgentState,
    AgentStatus,
    InMemoryAgentStateStore,
    PendingApproval,
)


@pytest.mark.asyncio
async def test_save_and_load_agent_state():
    store = InMemoryAgentStateStore()

    state = AgentState()
    state.mark_running()
    state.steps = 2
    state.mark_completed("done")

    await store.save(state)

    loaded = await store.load(state.agent_run_id)

    assert loaded is not None
    assert loaded.agent_run_id == state.agent_run_id
    assert loaded.status == AgentStatus.COMPLETED
    assert loaded.final_output == "done"


@pytest.mark.asyncio
async def test_load_missing_state_returns_none():
    store = InMemoryAgentStateStore()

    loaded = await store.load("missing")

    assert loaded is None


@pytest.mark.asyncio
async def test_save_paused_state_with_pending_approval():
    store = InMemoryAgentStateStore()

    state = AgentState()
    state.mark_running()
    state.mark_paused(
        PendingApproval(
            tool_name="dangerous_test_action",
            arguments={"resource_id": "ORD-123", "amount": 49.99},
            call_id="call_1",
        )
    )

    await store.save(state)

    loaded = await store.load(state.agent_run_id)

    assert loaded is not None
    assert loaded.status == AgentStatus.PAUSED
    assert loaded.pending_approval is not None
    assert loaded.pending_approval.tool_name == "dangerous_test_action"


@pytest.mark.asyncio
async def test_delete_state():
    store = InMemoryAgentStateStore()

    state = AgentState()
    await store.save(state)

    await store.delete(state.agent_run_id)

    assert await store.load(state.agent_run_id) is None


@pytest.mark.asyncio
async def test_clear_store():
    store = InMemoryAgentStateStore()

    state = AgentState()
    await store.save(state)

    await store.clear()

    assert await store.load(state.agent_run_id) is None
