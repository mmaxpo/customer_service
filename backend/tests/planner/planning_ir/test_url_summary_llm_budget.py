from app.tcos.compiler import compile_business_plan
from app.tcos.compiler.execution_ir import execution_graph_to_runtime_workflow
from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)


def test_url_summary_llm_node_uses_non_tiny_output_budget():
    result = compile_business_plan(
        build_url_summary_business_plan(
            "Summarize this URL for me: https://example.com"
        )
    )

    assert result.ok is True

    workflow = execution_graph_to_runtime_workflow(result.execution_graph)
    summarize = next(
        node for node in workflow["nodes"] if node["id"] == "summarize_content"
    )

    assert summarize["data"]["max_tokens"] >= 900
    assert summarize["data"]["token_budget_mode"] == "standard"
