from .run_state import RunState


def save_snapshot(state: RunState) -> dict:
    return state.snapshot()


def restore_snapshot(data: dict) -> RunState:
    state = RunState()
    state.input = data["input"]
    state.vars = data["vars"]
    state.memory = data["memory"]
    state.results = data["results"]
    state.meta = data["meta"]
    state.errors = data["errors"]
    state.status = data["status"]
    return state
