from __future__ import annotations

import pytest

from app.runtime.objectives.learning import (
    ObjectiveLearningDimensionDefinition,
    ObjectiveLearningDimensionKind,
    ObjectiveLearningProfile,
    ObjectiveLearningProfileRegistry,
    ObjectiveLearningQualificationPolicy,
    build_default_objective_learning_profile_registry,
)


def profile(
    *,
    version: int,
    namespace: str = "customer_service.support",
    objective_type: str = "multi_operation",
    profile_ref: str = ("customer_service.support.multi_operation"),
):
    return ObjectiveLearningProfile(
        profile_ref=profile_ref,
        profile_version=version,
        objective_namespace=namespace,
        objective_type=objective_type,
        dimensions=(
            ObjectiveLearningDimensionDefinition(
                key="required_evidence",
                kind=(ObjectiveLearningDimensionKind.REQUIRED_EVIDENCE),
                schema_ref=("objective_learning.dimension.required_evidence.v1"),
                schema_version=1,
                description=("Evidence required for qualification."),
            ),
        ),
        qualification_policy=(
            ObjectiveLearningQualificationPolicy(
                policy_ref=("objective_learning.policy.default"),
                policy_version=1,
                required_dimension_keys=("required_evidence",),
            )
        ),
    )


def test_register_and_resolve_latest_profile():
    registry = ObjectiveLearningProfileRegistry()

    first = profile(version=1)
    second = profile(version=2)

    registry.register(first)
    registry.register(second)

    assert registry.has(
        namespace="CUSTOMER_SERVICE.SUPPORT",
        objective_type="MULTI_OPERATION",
    )
    assert (
        registry.get(
            namespace="customer_service.support",
            objective_type="multi_operation",
        )
        is second
    )
    assert (
        registry.get(
            namespace="customer_service.support",
            objective_type="multi_operation",
            profile_version=1,
        )
        is first
    )
    assert registry.versions(
        namespace="customer_service.support",
        objective_type="multi_operation",
    ) == (1, 2)


def test_duplicate_version_is_rejected():
    registry = ObjectiveLearningProfileRegistry()
    registry.register(profile(version=1))

    with pytest.raises(
        ValueError,
        match="version already registered",
    ):
        registry.register(profile(version=1))


def test_profile_identity_cannot_move_between_objectives():
    registry = ObjectiveLearningProfileRegistry()

    registry.register(profile(version=1))

    with pytest.raises(
        ValueError,
        match="another objective family",
    ):
        registry.register(
            profile(
                version=1,
                namespace="another.namespace",
                objective_type="another_type",
            )
        )


def test_unknown_profile_is_rejected():
    registry = ObjectiveLearningProfileRegistry()

    with pytest.raises(
        ValueError,
        match="No objective learning profile",
    ):
        registry.get(
            namespace="missing",
            objective_type="missing",
        )


@pytest.mark.parametrize(
    ("namespace", "objective_type", "message"),
    [
        (
            "",
            "test",
            "namespace is required",
        ),
        (
            "example",
            "",
            "objective_type is required",
        ),
    ],
)
def test_blank_registry_identity_is_rejected(
    namespace,
    objective_type,
    message,
):
    registry = ObjectiveLearningProfileRegistry()

    with pytest.raises(
        ValueError,
        match=message,
    ):
        registry.has(
            namespace=namespace,
            objective_type=objective_type,
        )


def test_keys_are_deterministic():
    registry = ObjectiveLearningProfileRegistry()

    registry.register(
        profile(
            version=2,
            namespace="z",
            objective_type="b",
            profile_ref="z.b",
        )
    )
    registry.register(
        profile(
            version=1,
            namespace="a",
            objective_type="z",
            profile_ref="a.z",
        )
    )
    registry.register(
        profile(
            version=1,
            namespace="a",
            objective_type="a",
            profile_ref="a.a",
        )
    )

    assert registry.keys() == (
        ("a", "a", 1),
        ("a", "z", 1),
        ("z", "b", 2),
    )


def test_default_registry_is_empty_and_product_neutral():
    registry = build_default_objective_learning_profile_registry()

    assert registry.keys() == ()
