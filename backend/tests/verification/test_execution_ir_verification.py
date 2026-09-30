from app.tcos.planner.business_ir import (
    BusinessEdge,
    BusinessGoal,
    BusinessPlan,
    BusinessTaskCategory,
    task_with_capability,
)
from app.tcos.planner.runtime.plan_candidate import PlanCandidate
from app.tcos.verification.execution_ir import verify_candidate_compilation


def test_execution_ir_verification_passes_for_compilable_candidate():
    candidate = PlanCandidate(
        id="candidate",
        source="test",
        business_plan=BusinessPlan(
            id="p",
            goal=BusinessGoal(id="g", title="Goal"),
            tasks=[
                task_with_capability(
                    task_id="reply",
                    name="Reply",
                    category=BusinessTaskCategory.COMMUNICATION,
                    capability_id="runtime.response",
                )
            ],
        ),
    )

    result = verify_candidate_compilation(candidate)

    assert result.passed is True
    assert result.issues == []


def test_execution_ir_verification_fails_for_uncompilable_candidate():
    candidate = PlanCandidate(
        id="candidate",
        source="test",
        business_plan=BusinessPlan(
            id="p",
            goal=BusinessGoal(id="g", title="Goal"),
            tasks=[
                task_with_capability(
                    task_id="bad",
                    name="Bad",
                    category=BusinessTaskCategory.ACTION,
                    capability_id="missing.capability",
                )
            ],
        ),
    )

    result = verify_candidate_compilation(candidate)

    assert result.passed is False
    assert result.issues


def test_execution_ir_verification_accepts_injected_semantic_capability():
    candidate = PlanCandidate(
        id="semantic_candidate",
        source="test",
        business_plan=BusinessPlan(
            id="semantic_plan",
            goal=BusinessGoal(
                id="semantic_goal",
                title="Semantic capability",
            ),
            tasks=[
                task_with_capability(
                    task_id="semantic",
                    name="Semantic",
                    category=BusinessTaskCategory.ACTION,
                    capability_id="example.semantic.read",
                ),
                task_with_capability(
                    task_id="response",
                    name="Response",
                    category=BusinessTaskCategory.COMMUNICATION,
                    capability_id="runtime.response",
                ),
            ],
            edges=[
                BusinessEdge(
                    id="semantic_to_response",
                    source="semantic",
                    target="response",
                ),
            ],
        ),
    )

    result = verify_candidate_compilation(
        candidate,
        is_semantic_capability={"example.semantic.read"}.__contains__,
    )

    assert result.passed is True
    assert result.issues == []


def test_execution_ir_verification_accepts_injected_runtime_node():
    candidate = PlanCandidate(
        id="runtime-node-candidate",
        source="test",
        business_plan=BusinessPlan(
            id="runtime-node-plan",
            goal=BusinessGoal(
                id="runtime-node-goal",
                title="Runtime node",
            ),
            tasks=[
                task_with_capability(
                    task_id="runtime-node",
                    name="Runtime node",
                    category=BusinessTaskCategory.ACTION,
                    capability_id="product.custom.extract",
                ),
                task_with_capability(
                    task_id="response",
                    name="Response",
                    category=BusinessTaskCategory.COMMUNICATION,
                    capability_id="runtime.response",
                ),
            ],
            edges=[
                BusinessEdge(
                    id="runtime-node-to-response",
                    source="runtime-node",
                    target="response",
                )
            ],
        ),
    )

    result = verify_candidate_compilation(
        candidate,
        runtime_node_for_capability=lambda capability_id: (
            "custom.extract"
            if capability_id == "product.custom.extract"
            else None
        ),
    )

    assert result.passed is True
    assert result.issues == []
