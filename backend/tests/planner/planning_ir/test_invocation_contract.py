from app.tcos.compiler import compile_business_plan, compile_planning_plan
from app.tcos.compiler.execution_ir import execution_graph_to_runtime_workflow
from app.tcos.planner.business_ir.generic_examples import (
    build_url_summary_business_plan,
)
from app.tcos.planner.planning_builder import PlanningBuilder
from app.tcos.planner.planning_ir import (
    InvocationExecutionPolicy,
    InvocationInput,
    InvocationOutput,
    PlanningCapabilityInvocation,
    PlanningOperation,
    PlanningPlan,
)


def test_builder_populates_invocation_inputs_and_outputs():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )
    planning = PlanningBuilder().build(business)

    fetch = next(op for op in planning.operations if op.id == "fetch_url")
    summarize = next(op for op in planning.operations if op.id == "summarize_content")
    response = next(op for op in planning.operations if op.id == "send_response")

    assert fetch.invocation.outputs[0].artifact_id == "web_extract"
    assert summarize.invocation.inputs[0].artifact_id == "web_extract"
    assert summarize.invocation.outputs[0].artifact_id == "summary"
    assert response.invocation.inputs[0].artifact_id == "summary"


def test_invocation_execution_policy_model():
    invocation = PlanningCapabilityInvocation(
        capability_id="runtime.web_search",
        arguments={"query": "Tajeran"},
        execution=InvocationExecutionPolicy(
            timeout_ms=5000,
            retry_count=2,
            retry_backoff_ms=100,
            priority=80,
        ),
    )

    assert invocation.execution.timeout_ms == 5000
    assert invocation.execution.retry_count == 2
    assert invocation.execution.retry_backoff_ms == 100
    assert invocation.execution.priority == 80


def test_compiler_uses_invocation_io_over_operation_io():
    plan = PlanningPlan(
        id="planning_contract",
        business_plan_id="business_contract",
        operations=[
            PlanningOperation(
                id="produce",
                business_task_id="produce",
                objective="Produce",
                operation_type="acquire_information",
                selected_capability="runtime.web_search",
                invocation=PlanningCapabilityInvocation(
                    capability_id="runtime.web_search",
                    arguments={"query": "Tajeran"},
                    outputs=[
                        InvocationOutput(
                            artifact_id="invocation_input", kind="knowledge"
                        )
                    ],
                ),
            ),
            PlanningOperation(
                id="reply",
                business_task_id="reply",
                objective="Reply",
                operation_type="communicate",
                selected_capability="runtime.response",
                consumes=[],
                produces=[],
                invocation=PlanningCapabilityInvocation(
                    capability_id="runtime.response",
                    arguments={"answer_from": "last"},
                    inputs=[InvocationInput(artifact_id="invocation_input")],
                    outputs=[
                        InvocationOutput(
                            artifact_id="invocation_output", kind="response"
                        )
                    ],
                ),
            ),
        ],
        metadata={
            "extra": {
                "business_edges": [
                    {
                        "id": "edge_produce_to_reply",
                        "source": "produce",
                        "target": "reply",
                    }
                ]
            }
        },
    )

    result = compile_planning_plan(plan)

    assert result.ok is True
    node = next(node for node in result.execution_graph.nodes if node.id == "reply")
    assert node.inputs == [{"artifact_id": "invocation_input", "required": True}]
    assert node.outputs == [{"artifact_id": "invocation_output", "kind": "response"}]


def test_compiler_preserves_invocation_contract_in_execution_node_metadata():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    result = compile_business_plan(business)

    assert result.ok is True

    summarize = next(
        node for node in result.execution_graph.nodes if node.id == "summarize_content"
    )

    contract = summarize.metadata["invocation_contract"]

    assert contract["capability_id"] == "runtime.llm_generate"
    assert contract["inputs"][0]["artifact_id"] == "web_extract"
    assert contract["outputs"][0]["artifact_id"] == "summary"


def test_runtime_workflow_serialization_preserves_execution_artifacts():
    business = build_url_summary_business_plan(
        "Summarize this URL for me: https://example.com"
    )

    result = compile_business_plan(business)

    assert result.ok is True

    workflow = execution_graph_to_runtime_workflow(result.execution_graph)
    summarize = next(
        node for node in workflow["nodes"] if node["id"] == "summarize_content"
    )

    assert summarize["data"]["inputs"][0]["artifact_id"] == "web_extract"
    assert summarize["data"]["outputs"][0]["artifact_id"] == "summary"
