class WorkflowRepo:
    def __init__(self):
        self._store = {}

    async def add(self, wf_id: str, wf: dict):
        self._store[wf_id] = wf

    async def get_workflow(self, wf_id: str):
        return self._store.get(wf_id)
