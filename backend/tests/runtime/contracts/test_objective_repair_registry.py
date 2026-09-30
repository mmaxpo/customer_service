import pytest

from app.runtime.objectives.repair import (
    ObjectiveRepairAction,
    ObjectiveRepairDisposition,
    ObjectiveRepairPlan,
    ObjectiveRepairPlanner,
    ObjectiveRepairPlannerNotFoundError,
    ObjectiveRepairPlannerRegistry,
    build_default_objective_repair_registry,
)


class ExamplePlanner:
    def plan_repair(self, context):
        target_ref = (
            context.request.targets[0]
            .operation_ref
        )

        return ObjectiveRepairPlan(
            repair_request_ref=(
                context.request
                .repair_request_ref
            ),
            objective=(
                context.request.source.objective
            ),
            disposition=(
                ObjectiveRepairDisposition
                .RETRY_OPERATION
            ),
            reason_code="retryable",
            summary="Retry.",
            confidence=0.9,
            actions=(
                ObjectiveRepairAction(
                    action_ref="action-1",
                    disposition=(
                        ObjectiveRepairDisposition
                        .RETRY_OPERATION
                    ),
                    target_operation_refs=(
                        target_ref,
                    ),
                    reason_code="retryable",
                    summary="Retry.",
                    confidence=0.9,
                ),
            ),
            planned_target_refs=(
                target_ref,
            ),
        )


class InvalidPlanner:
    pass


def test_planner_protocol_runtime_check():
    assert isinstance(
        ExamplePlanner(),
        ObjectiveRepairPlanner,
    )

    assert not isinstance(
        InvalidPlanner(),
        ObjectiveRepairPlanner,
    )


def test_register_and_resolve_normalizes_key():
    registry = ObjectiveRepairPlannerRegistry()
    planner = ExamplePlanner()

    registry.register(
        namespace=" Example.Support ",
        objective_type=" Refund ",
        planner=planner,
    )

    assert registry.resolve(
        namespace="example.support",
        objective_type="refund",
    ) is planner

    assert registry.contains(
        namespace="EXAMPLE.SUPPORT",
        objective_type="REFUND",
    )


def test_duplicate_registration_is_rejected():
    registry = ObjectiveRepairPlannerRegistry()

    registry.register(
        namespace="example.support",
        objective_type="refund",
        planner=ExamplePlanner(),
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register(
            namespace="example.support",
            objective_type="refund",
            planner=ExamplePlanner(),
        )


@pytest.mark.parametrize(
    ("namespace", "objective_type"),
    [
        ("", "refund"),
        ("example.support", ""),
        ("   ", "refund"),
        ("example.support", "   "),
    ],
)
def test_blank_registry_key_is_rejected(
    namespace,
    objective_type,
):
    registry = ObjectiveRepairPlannerRegistry()

    with pytest.raises(
        ValueError,
        match="required",
    ):
        registry.register(
            namespace=namespace,
            objective_type=objective_type,
            planner=ExamplePlanner(),
        )


def test_invalid_planner_is_rejected():
    registry = ObjectiveRepairPlannerRegistry()

    with pytest.raises(
        TypeError,
        match="ObjectiveRepairPlanner",
    ):
        registry.register(
            namespace="example.support",
            objective_type="refund",
            planner=InvalidPlanner(),
        )


def test_unknown_planner_error_is_stable():
    registry = ObjectiveRepairPlannerRegistry()

    with pytest.raises(
        ObjectiveRepairPlannerNotFoundError,
        match=(
            "objective repair planner not found for "
            "example.support:refund"
        ),
    ):
        registry.resolve(
            namespace="Example.Support",
            objective_type="Refund",
        )


def test_registered_keys_are_sorted():
    registry = ObjectiveRepairPlannerRegistry()

    registry.register(
        namespace="zeta",
        objective_type="two",
        planner=ExamplePlanner(),
    )
    registry.register(
        namespace="alpha",
        objective_type="one",
        planner=ExamplePlanner(),
    )

    assert registry.registered_keys() == (
        ("alpha", "one"),
        ("zeta", "two"),
    )


def test_default_registry_is_product_neutral():
    registry = (
        build_default_objective_repair_registry()
    )

    assert registry.registered_keys() == ()
