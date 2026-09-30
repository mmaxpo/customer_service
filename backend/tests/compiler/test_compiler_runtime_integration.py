from app.tcos.compiler import compile_business_plan
from app.tcos.compiler.execution_ir import execution_graph_to_runtime_workflow
from app.tcos.planner.business_ir.generic_examples import build_url_summary_business_plan
from app.runtime.engine.validator import validate_workflow


def test_compiled_workflow_is_valid_runtime_workflow():
    plan = build_url_summary_business_plan("Summarize https://example.com")

    result = compile_business_plan(plan)

    assert result.ok

    workflow = execution_graph_to_runtime_workflow(result.execution_graph)

    errors = validate_workflow(workflow)

    assert errors == []


def test_every_execution_node_has_runtime_node_type():
    plan = build_url_summary_business_plan("Summarize https://example.com")

    result = compile_business_plan(plan)

    graph = result.execution_graph

    runtime_types = {node.node_type for node in graph.nodes}

    assert "trigger.message" in runtime_types
    assert "web.fetch_extract" in runtime_types
    assert "llm.generate" in runtime_types
    assert "response" in runtime_types


def test_execution_graph_serialization_preserves_node_count():
    plan = build_url_summary_business_plan("Summarize https://example.com")

    result = compile_business_plan(plan)

    graph = result.execution_graph

    workflow = execution_graph_to_runtime_workflow(graph)

    assert len(workflow["nodes"]) == len(graph.nodes)
    assert len(workflow["edges"]) == len(graph.edges)


def test_business_task_metadata_is_preserved():
    plan = build_url_summary_business_plan("Summarize https://example.com")

    result = compile_business_plan(plan)

    graph = result.execution_graph

    for node in graph.nodes:
        if node.id == "trigger":
            continue

        assert "business_task_id" in node.metadata
        assert "capability_id" in node.metadata


def test_trigger_is_always_first_node():
    plan = build_url_summary_business_plan("Summarize https://example.com")

    result = compile_business_plan(plan)

    graph = result.execution_graph

    assert graph.nodes[0].id == "trigger"
    assert graph.nodes[0].node_type == "trigger.message"
