from app.tcos.compiler import compile_planning_plan
from app.tcos.planner.planning_ir import (
    PlanningCapabilityInvocation,
    PlanningMetadata,
    PlanningOperation,
    PlanningPlan,
)


def _metadata_with_edge(source: str, target: str) -> PlanningMetadata:
    return PlanningMetadata(
        extra={
            "business_edges": [
                {"id": f"edge_{source}_to_{target}", "source": source, "target": target}
            ]
        }
    )


def test_compile_planning_plan_uses_invocation_arguments():
    plan = PlanningPlan(
        id="planning_url",
        business_plan_id="business_url",
        operations=[
            PlanningOperation(
                id="fetch_url",
                business_task_id="fetch_url",
                objective="Acquire web page",
                operation_type="acquire_information",
                selected_capability="runtime.web_fetch_extract",
                invocation=PlanningCapabilityInvocation(
                    capability_id="runtime.web_fetch_extract",
                    arguments={
                        "url": "https://example.com",
                        "artifact_as": "web_extract",
                    },
                ),
            ),
            PlanningOperation(
                id="reply",
                business_task_id="reply",
                objective="Reply",
                operation_type="communicate",
                selected_capability="runtime.response",
                invocation=PlanningCapabilityInvocation(
                    capability_id="runtime.response",
                    arguments={"answer_from": "last"},
                ),
            ),
        ],
        metadata=_metadata_with_edge("fetch_url", "reply"),
    )

    result = compile_planning_plan(plan)

    assert result.ok is True
    node = next(node for node in result.execution_graph.nodes if node.id == "fetch_url")
    assert node.node_type == "web.fetch_extract"
    assert node.config["url"] == "https://example.com"
    assert node.config["artifact_as"] == "web_extract"


def test_compile_planning_plan_uses_invocation_capability_over_selected_capability():
    plan = PlanningPlan(
        id="planning_response",
        business_plan_id="business_response",
        operations=[
            PlanningOperation(
                id="reply",
                business_task_id="reply",
                objective="Reply",
                operation_type="communicate",
                selected_capability="runtime.web_search",
                invocation=PlanningCapabilityInvocation(
                    capability_id="runtime.response",
                    arguments={"answer_from": "last"},
                ),
            )
        ],
    )

    result = compile_planning_plan(plan)

    assert result.ok is True
    node = next(node for node in result.execution_graph.nodes if node.id == "reply")
    assert node.node_type == "response"
    assert node.metadata["capability_id"] == "runtime.response"


def test_compile_planning_plan_maps_invocation_execution_controls():
    plan = PlanningPlan(
        id="planning_retry",
        business_plan_id="business_retry",
        operations=[
            PlanningOperation(
                id="search",
                business_task_id="search",
                objective="Search",
                operation_type="acquire_information",
                selected_capability="runtime.web_search",
                invocation=PlanningCapabilityInvocation(
                    capability_id="runtime.web_search",
                    arguments={"query": "Tajeran"},
                    timeout_ms=5000,
                    retry_count=2,
                ),
            ),
            PlanningOperation(
                id="reply",
                business_task_id="reply",
                objective="Reply",
                operation_type="communicate",
                selected_capability="runtime.response",
                invocation=PlanningCapabilityInvocation(
                    capability_id="runtime.response",
                    arguments={"answer_from": "last"},
                ),
            ),
        ],
        metadata=_metadata_with_edge("search", "reply"),
    )

    result = compile_planning_plan(plan)

    assert result.ok is True
    node = next(node for node in result.execution_graph.nodes if node.id == "search")
    assert node.config["timeout_ms"] == 5000
    assert node.config["retries"] == 2
