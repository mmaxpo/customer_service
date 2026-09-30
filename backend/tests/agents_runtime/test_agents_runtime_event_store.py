import pytest

from app.agents_runtime.events import (
    AgentEvent,
    AgentEventType,
    InMemoryAgentEventStore,
)


@pytest.mark.asyncio
async def test_append_and_list_events_by_agent_run_id():
    store = InMemoryAgentEventStore()

    event = AgentEvent(
        agent_run_id="run-1",
        type=AgentEventType.RUN_STARTED,
        step=0,
        sequence=1,
        payload={"input": "hello"},
    )

    await store.append(event)

    events = await store.list_by_agent_run_id("run-1")

    assert len(events) == 1
    assert events[0].type == AgentEventType.RUN_STARTED
    assert events[0].payload == {"input": "hello"}


@pytest.mark.asyncio
async def test_events_are_isolated_by_agent_run_id():
    store = InMemoryAgentEventStore()

    await store.append(
        AgentEvent(
            agent_run_id="run-1",
            type=AgentEventType.RUN_STARTED,
            step=0,
            sequence=1,
        )
    )

    await store.append(
        AgentEvent(
            agent_run_id="run-2",
            type=AgentEventType.RUN_STARTED,
            step=0,
            sequence=1,
        )
    )

    assert len(await store.list_by_agent_run_id("run-1")) == 1
    assert len(await store.list_by_agent_run_id("run-2")) == 1
    assert await store.list_by_agent_run_id("missing") == []


@pytest.mark.asyncio
async def test_append_many():
    store = InMemoryAgentEventStore()

    events = [
        AgentEvent(
            agent_run_id="run-1",
            type=AgentEventType.RUN_STARTED,
            step=0,
            sequence=1,
        ),
        AgentEvent(
            agent_run_id="run-1",
            type=AgentEventType.RUN_COMPLETED,
            step=1,
            sequence=2,
        ),
    ]

    await store.append_many(events)

    stored = await store.list_by_agent_run_id("run-1")

    assert [event.sequence for event in stored] == [1, 2]


@pytest.mark.asyncio
async def test_clear_store():
    store = InMemoryAgentEventStore()

    await store.append(
        AgentEvent(
            agent_run_id="run-1",
            type=AgentEventType.RUN_STARTED,
            step=0,
            sequence=1,
        )
    )

    await store.clear()

    assert await store.list_by_agent_run_id("run-1") == []
