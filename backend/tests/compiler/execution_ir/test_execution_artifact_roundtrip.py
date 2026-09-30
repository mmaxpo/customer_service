from app.tcos.compiler import compile_business_plan
from app.tcos.compiler.execution_ir import (
    execution_graph_from_runtime_workflow,
    execution_graph_to_runtime_workflow,
)
from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)


def test_execution_artifacts_survive_runtime_workflow_roundtrip():
    result = compile_business_plan(
        build_url_summary_business_plan(
            "Summarize this URL for me: https://example.com"
        )
    )

    assert result.ok is True

    workflow = execution_graph_to_runtime_workflow(result.execution_graph)
    roundtrip = execution_graph_from_runtime_workflow(
        workflow,
        graph_id="roundtrip_url_summary",
    )

    summarize = next(node for node in roundtrip.nodes if node.id == "summarize_content")
    response = next(node for node in roundtrip.nodes if node.id == "send_response")

    assert summarize.inputs == [{"artifact_id": "web_extract", "required": True}]
    assert summarize.outputs == [{"artifact_id": "summary", "kind": "text"}]
    assert response.inputs == [{"artifact_id": "summary", "required": True}]
