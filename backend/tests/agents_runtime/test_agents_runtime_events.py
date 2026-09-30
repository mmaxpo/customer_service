from app.agents_runtime.events import AgentEventType, EventRecorder


def test_emit_event():
    recorder = EventRecorder()

    event = recorder.emit(
        agent_run_id="run-1",
        event_type=AgentEventType.RUN_STARTED,
        step=0,
        payload={"input": "hello"},
    )

    assert event.agent_run_id == "run-1"
    assert event.type == AgentEventType.RUN_STARTED
    assert event.sequence == 1
    assert event.payload == {"input": "hello"}


def test_event_sequence_increments():
    recorder = EventRecorder()

    first = recorder.emit(
        agent_run_id="run-1",
        event_type=AgentEventType.RUN_STARTED,
        step=0,
    )

    second = recorder.emit(
        agent_run_id="run-1",
        event_type=AgentEventType.LLM_CALL_STARTED,
        step=1,
    )

    assert first.sequence == 1
    assert second.sequence == 2


def test_events_property_returns_copy():
    recorder = EventRecorder()

    recorder.emit(
        agent_run_id="run-1",
        event_type=AgentEventType.RUN_STARTED,
        step=0,
    )

    events = recorder.events
    events.clear()

    assert len(recorder.events) == 1


def test_by_type():
    recorder = EventRecorder()

    recorder.emit(
        agent_run_id="run-1",
        event_type=AgentEventType.RUN_STARTED,
        step=0,
    )

    recorder.emit(
        agent_run_id="run-1",
        event_type=AgentEventType.LLM_CALL_STARTED,
        step=1,
    )

    started = recorder.by_type(AgentEventType.RUN_STARTED)

    assert len(started) == 1
    assert started[0].type == AgentEventType.RUN_STARTED


def test_clear_events():
    recorder = EventRecorder()

    recorder.emit(
        agent_run_id="run-1",
        event_type=AgentEventType.RUN_STARTED,
        step=0,
    )

    recorder.clear()

    assert recorder.events == []
