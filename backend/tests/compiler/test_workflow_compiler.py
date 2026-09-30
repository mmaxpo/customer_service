from app.tcos.compiler import compile_business_plan
from app.tcos.compiler.execution_ir import execution_graph_to_runtime_workflow
from app.tcos.planner.business_ir.generic_examples import build_url_summary_business_plan


def test_compile_url_summary_business_plan_to_execution_ir():
    plan = build_url_summary_business_plan("Summarize https://example.com")

    result = compile_business_plan(plan)

    assert result.ok is True
    assert result.execution_graph is not None

    graph = result.execution_graph
    node_types = {node.id: node.node_type for node in graph.nodes}

    assert node_types["trigger"] == "trigger.message"
    assert node_types["fetch_url"] == "web.fetch_extract"
    assert node_types["summarize_content"] == "llm.generate"
    assert node_types["send_response"] == "response"


def test_compiled_execution_ir_serializes_to_runtime_workflow():
    result = compile_business_plan(build_url_summary_business_plan("Summarize https://example.com"))

    workflow = execution_graph_to_runtime_workflow(result.execution_graph)

    assert workflow["nodes"][0]["data"]["nodeType"] == "trigger.message"
    assert any(node["data"]["nodeType"] == "response" for node in workflow["nodes"])
    assert workflow["edges"]


def test_compile_rejects_task_without_capability():
    from app.tcos.planner.business_ir import (
        BusinessGoal,
        BusinessPlan,
        BusinessTask,
        BusinessTaskCategory,
    )

    plan = BusinessPlan(
        id="bad",
        goal=BusinessGoal(id="g", title="Goal"),
        tasks=[
            BusinessTask(
                id="task",
                name="Task",
                category=BusinessTaskCategory.ACTION,
            )
        ],
    )

    result = compile_business_plan(plan)

    assert result.ok is False
    assert any(d.code == "task_missing_capability" for d in result.diagnostics)
