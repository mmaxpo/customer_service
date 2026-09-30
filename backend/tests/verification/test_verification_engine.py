from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.planner.runtime.planner import Planner
from app.tcos.planner.runtime.planning_context import PlanningContext
from app.tcos.verification import VerificationEngine


def test_verification_passes_for_generic_plan():
    planner = Planner()
    goal = "Summarize https://example.com"

    candidate = planner.plan(
        intent=detect_intent(text=goal),
        context=PlanningContext(
            user_message=goal,
        ),
    )

    result = VerificationEngine().verify(
        candidate
    )

    assert result.passed is True
    assert result.issues == []


def test_verification_accepts_registered_semantic_capability():
    from app.tcos.planner.business_ir import (
        BusinessEdge,
        BusinessGoal,
        BusinessPlan,
        BusinessTaskCategory,
        task_with_capability,
    )
    from app.tcos.planner.runtime.plan_candidate import (
        PlanCandidate,
    )

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

    result = VerificationEngine().verify(
        candidate,
        is_semantic_capability={"example.semantic.read"}.__contains__,
    )

    assert result.passed is True
    assert result.issues == []


def test_verification_still_rejects_unregistered_semantic_id():
    from app.tcos.planner.business_ir import (
        BusinessGoal,
        BusinessPlan,
        BusinessTaskCategory,
        task_with_capability,
    )
    from app.tcos.planner.runtime.plan_candidate import (
        PlanCandidate,
    )

    candidate = PlanCandidate(
        id="unknown_semantic_candidate",
        source="test",
        business_plan=BusinessPlan(
            id="unknown_semantic_plan",
            goal=BusinessGoal(
                id="unknown_semantic_goal",
                title="Unknown semantic capability",
            ),
            tasks=[
                task_with_capability(
                    task_id="semantic",
                    name="Semantic",
                    category=(BusinessTaskCategory.ACTION),
                    capability_id=("example.semantic.unknown"),
                )
            ],
        ),
    )

    result = VerificationEngine().verify(
        candidate,
        is_semantic_capability=lambda _: False,
    )

    assert result.passed is False

    assert any(issue.code == "missing_capability" for issue in result.issues)


def test_verification_accepts_injected_runtime_node():
    from app.tcos.planner.business_ir import (
        BusinessEdge,
        BusinessGoal,
        BusinessPlan,
        BusinessTaskCategory,
        task_with_capability,
    )
    from app.tcos.planner.runtime.plan_candidate import (
        PlanCandidate,
    )

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

    result = VerificationEngine().verify(
        candidate,
        runtime_node_for_capability=lambda capability_id: (
            "custom.extract"
            if capability_id == "product.custom.extract"
            else None
        ),
    )

    assert result.passed is True
    assert result.issues == []
