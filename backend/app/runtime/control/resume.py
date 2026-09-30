def resume(state, input_data: dict):
    state.vars.update(input_data)
    state.status = "running"
