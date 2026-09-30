from app.tcos.compiler import compile_business_plan
from app.tcos.compiler.execution_ir import execution_graph_to_runtime_workflow
from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)


def test_response_artifact_answer_from_compiles_to_runtime_vars_key():
    result = compile_business_plan(
        build_url_summary_business_plan(
            "Summarize this URL for me: https://example.com"
        )
    )

    assert result.ok is True

    workflow = execution_graph_to_runtime_workflow(result.execution_graph)
    response = next(node for node in workflow["nodes"] if node["id"] == "send_response")

    assert response["data"]["answer_from"] == "vars"
    assert response["data"]["answer_key"] == "summary"
