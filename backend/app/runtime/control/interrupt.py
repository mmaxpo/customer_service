from app.runtime.errors.exceptions import InterruptSignal


def interrupt(payload: dict):
    raise InterruptSignal(payload)
