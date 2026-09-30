from app.tcos.compiler.execution_ir import (
    analyze_execution_graph,
    response_node,
    simple_runtime_graph,
    trigger_node,
    validate_execution_graph,
)


def test_simple_runtime_graph_factory_and_analyzer():
    graph = simple_runtime_graph(
        graph_id="g",
        nodes=[trigger_node(input_text="hello"), response_node()],
    )

    assert validate_execution_graph(graph) == []

    analysis = analyze_execution_graph(graph)

    assert analysis.node_count == 2
    assert analysis.edge_count == 1
    assert analysis.node_types == ["response", "trigger.message"]
    assert analysis.entry_nodes == ["trigger"]
    assert analysis.exit_nodes == ["response"]
