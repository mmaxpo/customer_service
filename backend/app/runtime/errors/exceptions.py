class WorkflowError(Exception):
    pass


class NodeExecutionError(WorkflowError):
    pass


class InterruptSignal(Exception):
    def __init__(self, payload: dict):
        self.payload = payload
