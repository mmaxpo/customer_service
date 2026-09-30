from app.tcos.execution import WorkflowRuntimeAdapter


def test_workflow_runtime_adapter_exists():
    adapter = WorkflowRuntimeAdapter()

    assert hasattr(adapter, "execute")
