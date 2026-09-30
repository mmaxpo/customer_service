from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.runtime.objectives.resolution import (
    ObjectiveReference,
    ObjectiveResolutionAdapterRegistry,
    ObjectiveResolutionAssessment,
    ObjectiveResolutionContext,
    ObjectiveResolutionSource,
    ObjectiveResolutionStatus,
)


@dataclass
class FakeAdapter:
    marker: str

    def assess(
        self,
        context: ObjectiveResolutionContext,
    ) -> ObjectiveResolutionAssessment:
        return ObjectiveResolutionAssessment(
            objective=ObjectiveReference(
                namespace="example",
                objective_type="test",
                objective_ref=self.marker,
                objective_version=1,
            ),
            source=ObjectiveResolutionSource(
                outcome_ref="outcome-1",
                outcome_version=1,
                evaluation_ref="evaluation-1",
                evaluation_version=1,
            ),
            status=(
                ObjectiveResolutionStatus.ACHIEVED
            ),
            reason_code="test",
            summary="Test.",
            confidence=1.0,
            is_terminal=True,
        )


def test_register_resolve_and_assess():
    registry = (
        ObjectiveResolutionAdapterRegistry()
    )
    adapter = FakeAdapter("adapter-1")

    registry.register(
        namespace=" Customer_Service.Support ",
        objective_type=" MULTI_OPERATION ",
        adapter=adapter,
    )

    assert registry.has(
        namespace="customer_service.support",
        objective_type="multi_operation",
    )
    assert registry.get(
        namespace="CUSTOMER_SERVICE.SUPPORT",
        objective_type="MULTI_OPERATION",
    ) is adapter

    result = registry.assess(
        namespace="customer_service.support",
        objective_type="multi_operation",
        context=ObjectiveResolutionContext(),
    )

    assert result.objective.objective_ref == (
        "adapter-1"
    )


def test_duplicate_registration_is_rejected():
    registry = (
        ObjectiveResolutionAdapterRegistry()
    )

    registry.register(
        namespace="example",
        objective_type="test",
        adapter=FakeAdapter("first"),
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register(
            namespace="EXAMPLE",
            objective_type="TEST",
            adapter=FakeAdapter("second"),
        )


def test_unknown_adapter_is_rejected():
    registry = (
        ObjectiveResolutionAdapterRegistry()
    )

    with pytest.raises(
        ValueError,
        match=(
            "No objective resolution adapter "
            "registered"
        ),
    ):
        registry.get(
            namespace="example",
            objective_type="missing",
        )


@pytest.mark.parametrize(
    ("namespace", "objective_type", "message"),
    [
        ("", "test", "namespace is required"),
        ("example", "", "objective_type is required"),
    ],
)
def test_blank_registry_identity_is_rejected(
    namespace,
    objective_type,
    message,
):
    registry = (
        ObjectiveResolutionAdapterRegistry()
    )

    with pytest.raises(
        ValueError,
        match=message,
    ):
        registry.register(
            namespace=namespace,
            objective_type=objective_type,
            adapter=FakeAdapter("test"),
        )


def test_keys_are_deterministic():
    registry = (
        ObjectiveResolutionAdapterRegistry()
    )

    registry.register(
        namespace="z",
        objective_type="b",
        adapter=FakeAdapter("1"),
    )
    registry.register(
        namespace="a",
        objective_type="z",
        adapter=FakeAdapter("2"),
    )
    registry.register(
        namespace="a",
        objective_type="a",
        adapter=FakeAdapter("3"),
    )

    assert registry.keys() == (
        ("a", "a"),
        ("a", "z"),
        ("z", "b"),
    )
