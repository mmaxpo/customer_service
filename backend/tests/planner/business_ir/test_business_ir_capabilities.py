from app.tcos.planner.business_ir import (
    BusinessGoal,
    BusinessPlan,
    BusinessTaskCategory,
    capability_ids_for_plan,
    missing_capability_ids,
    plan_capabilities_exist,
    task_with_capability,
    validate_business_plan,
)


def test_business_ir_capability_helpers_find_existing_capabilities():
    plan = BusinessPlan(
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
    )

    assert capability_ids_for_plan(plan) == ["runtime.response"]
    assert missing_capability_ids(plan) == []
    assert plan_capabilities_exist(plan) is True


def test_business_ir_validation_rejects_unknown_capability():
    plan = BusinessPlan(
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
    )

    errors = validate_business_plan(plan)

    assert any(error.code == "missing_capability" for error in errors)


def test_business_ir_accepts_injected_semantic_capability():
    plan = BusinessPlan(
        id="semantic-plan",
        goal=BusinessGoal(
            id="semantic-goal",
            title="Semantic capability",
        ),
        tasks=[
            task_with_capability(
                task_id="semantic",
                name="Semantic",
                category=BusinessTaskCategory.ACTION,
                capability_id="example.semantic.read",
            )
        ],
    )

    known = {
        "example.semantic.read",
    }

    errors = validate_business_plan(
        plan,
        is_semantic_capability=known.__contains__,
    )

    assert errors == []

    assert (
        missing_capability_ids(
            plan,
            is_semantic_capability=known.__contains__,
        )
        == []
    )

    assert (
        plan_capabilities_exist(
            plan,
            is_semantic_capability=known.__contains__,
        )
        is True
    )


def test_business_ir_does_not_trust_semantic_looking_id():
    plan = BusinessPlan(
        id="unknown-semantic-plan",
        goal=BusinessGoal(
            id="unknown-semantic-goal",
            title="Unknown semantic capability",
        ),
        tasks=[
            task_with_capability(
                task_id="semantic",
                name="Semantic",
                category=BusinessTaskCategory.ACTION,
                capability_id="ecommerce.fake.read",
            )
        ],
    )

    errors = validate_business_plan(
        plan,
        is_semantic_capability=lambda _: False,
    )

    assert any(error.code == "missing_capability" for error in errors)

    assert missing_capability_ids(
        plan,
        is_semantic_capability=lambda _: False,
    ) == [
        "ecommerce.fake.read",
    ]


def test_business_ir_default_remains_closed_world():
    plan = BusinessPlan(
        id="default-closed-world-plan",
        goal=BusinessGoal(
            id="default-closed-world-goal",
            title="Default validation",
        ),
        tasks=[
            task_with_capability(
                task_id="semantic",
                name="Semantic",
                category=BusinessTaskCategory.ACTION,
                capability_id="example.semantic.read",
            )
        ],
    )

    assert missing_capability_ids(plan) == [
        "example.semantic.read",
    ]

    assert plan_capabilities_exist(plan) is False

    errors = validate_business_plan(plan)

    assert any(error.code == "missing_capability" for error in errors)


def test_business_ir_accepts_injected_runtime_node():
    plan = BusinessPlan(
        id="runtime-node-plan",
        goal=BusinessGoal(
            id="runtime-node-goal",
            title="Runtime node capability",
        ),
        tasks=[
            task_with_capability(
                task_id="runtime-node",
                name="Runtime node",
                category=BusinessTaskCategory.ACTION,
                capability_id="product.custom.extract",
            )
        ],
    )

    resolver = lambda capability_id: (
        "custom.extract"
        if capability_id == "product.custom.extract"
        else None
    )

    assert (
        missing_capability_ids(
            plan,
            runtime_node_for_capability=resolver,
        )
        == []
    )

    assert (
        plan_capabilities_exist(
            plan,
            runtime_node_for_capability=resolver,
        )
        is True
    )

    assert (
        validate_business_plan(
            plan,
            runtime_node_for_capability=resolver,
        )
        == []
    )
