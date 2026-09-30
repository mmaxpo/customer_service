import asyncio

import pytest

from app.agents_runtime.events import AgentEvent, AgentEventStream, AgentEventType


@pytest.mark.asyncio
async def test_subscriber_receives_published_event():
    stream = AgentEventStream()

    async def consume_one():
        async for event in stream.subscribe("run-1"):
            return event

    task = asyncio.create_task(consume_one())

    await asyncio.sleep(0)

    assert stream.subscriber_count("run-1") == 1

    event = AgentEvent(
        agent_run_id="run-1",
        type=AgentEventType.RUN_STARTED,
        step=0,
        sequence=1,
    )

    await stream.publish(event)

    received = await asyncio.wait_for(task, timeout=1)

    assert received.agent_run_id == "run-1"
    assert received.type == AgentEventType.RUN_STARTED


@pytest.mark.asyncio
async def test_event_isolated_by_agent_run_id():
    stream = AgentEventStream()

    async def consume_one():
        async for event in stream.subscribe("run-1"):
            return event

    task = asyncio.create_task(consume_one())

    await asyncio.sleep(0)

    await stream.publish(
        AgentEvent(
            agent_run_id="run-2",
            type=AgentEventType.RUN_STARTED,
            step=0,
            sequence=1,
        )
    )

    await asyncio.sleep(0.01)

    assert not task.done()

    await stream.publish(
        AgentEvent(
            agent_run_id="run-1",
            type=AgentEventType.RUN_STARTED,
            step=0,
            sequence=1,
        )
    )

    received = await asyncio.wait_for(task, timeout=1)

    assert received.agent_run_id == "run-1"


@pytest.mark.asyncio
async def test_subscriber_removed_when_generator_closes():
    stream = AgentEventStream()

    gen = stream.subscribe("run-1")

    task = asyncio.create_task(gen.__anext__())

    await asyncio.sleep(0)

    assert stream.subscriber_count("run-1") == 1

    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass

    await asyncio.sleep(0)

    assert stream.subscriber_count("run-1") == 0


@pytest.mark.asyncio
async def test_publish_without_subscribers_does_not_fail():
    stream = AgentEventStream()

    await stream.publish(
        AgentEvent(
            agent_run_id="run-1",
            type=AgentEventType.RUN_STARTED,
            step=0,
            sequence=1,
        )
    )

    assert stream.subscriber_count("run-1") == 0
