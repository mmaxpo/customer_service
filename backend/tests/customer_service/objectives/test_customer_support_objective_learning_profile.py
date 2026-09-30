from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domains.customer_service.services.support.learning.objective_learning_profiles import (
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_DIMENSIONS,
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
    CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
    FAILURE_PATTERN_DIMENSION,
    PLAN_STRUCTURE_DIMENSION,
    PROVIDER_CONSTRAINT_DIMENSION,
    REPAIR_STRATEGY_DIMENSION,
    REQUIRED_EVIDENCE_DIMENSION,
    VALIDITY_CONTEXT_DIMENSION,
    build_customer_support_objective_learning_profile,
    register_customer_support_objective_learning_profiles,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningDimensionKind,
    ObjectiveLearningProfile,
    ObjectiveLearningProfileRegistry,
    build_default_objective_learning_profile_registry,
)


def test_customer_support_profile_owns_expected_dimensions():
    profile = build_customer_support_objective_learning_profile()

    assert profile.profile_ref == (CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF)
    assert profile.profile_version == 1
    assert profile.objective_namespace == (CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE)
    assert profile.objective_type == (CUSTOMER_SUPPORT_OBJECTIVE_TYPE)

    assert (
        tuple(dimension.key for dimension in profile.dimensions)
        == CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_DIMENSIONS
    )

    by_key = {dimension.key: dimension for dimension in profile.dimensions}

    assert by_key[REQUIRED_EVIDENCE_DIMENSION].kind == (
        ObjectiveLearningDimensionKind.REQUIRED_EVIDENCE
    )
    assert by_key[PLAN_STRUCTURE_DIMENSION].kind == (
        ObjectiveLearningDimensionKind.PLAN_STRUCTURE
    )
    assert by_key[PROVIDER_CONSTRAINT_DIMENSION].kind == (
        ObjectiveLearningDimensionKind.PROVIDER_CONSTRAINT
    )
    assert by_key[FAILURE_PATTERN_DIMENSION].kind == (
        ObjectiveLearningDimensionKind.FAILURE_PATTERN
    )
    assert by_key[REPAIR_STRATEGY_DIMENSION].kind == (
        ObjectiveLearningDimensionKind.REPAIR_STRATEGY
    )
    assert by_key[VALIDITY_CONTEXT_DIMENSION].kind == (
        ObjectiveLearningDimensionKind.VALIDITY_CONTEXT
    )


def test_required_dimensions_match_qualification_policy():
    profile = build_customer_support_objective_learning_profile()

    assert profile.qualification_policy.required_dimension_keys == (
        REQUIRED_EVIDENCE_DIMENSION,
        PLAN_STRUCTURE_DIMENSION,
        VALIDITY_CONTEXT_DIMENSION,
    )

    required_by_definition = tuple(
        item.key for item in profile.dimensions if item.required_for_qualification
    )

    assert required_by_definition == (
        profile.qualification_policy.required_dimension_keys
    )


def test_customer_support_policy_is_safe_and_advisory():
    policy = build_customer_support_objective_learning_profile().qualification_policy

    assert policy.policy_ref == (CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF)
    assert policy.require_terminal_resolution is True
    assert policy.require_verification is True
    assert policy.allow_achieved is True
    assert policy.allow_repaired_achievement is True
    assert policy.explicit_approval_required is True

    assert policy.informational_only is True
    assert policy.affects_ranking is False
    assert policy.affects_capability_selection is False
    assert policy.affects_business_plan is False
    assert policy.selects_provider is False
    assert policy.authorizes_execution is False
    assert policy.bypasses_approval is False
    assert policy.bypasses_verification is False


def test_profile_thresholds_are_configurable_by_version():
    first = build_customer_support_objective_learning_profile(
        profile_version=1,
        policy_version=1,
        minimum_confidence=0.90,
        minimum_evidence_count=1,
        minimum_effective_sample_size=1.0,
        maximum_contradiction_score=0.20,
        minimum_stability_score=0.80,
    )
    second = build_customer_support_objective_learning_profile(
        profile_version=2,
        policy_version=2,
        minimum_confidence=0.97,
        minimum_evidence_count=3,
        minimum_evidence_coverage=0.95,
        minimum_effective_sample_size=5.0,
        maximum_contradiction_score=0.10,
        minimum_stability_score=0.95,
        allow_partially_achieved=True,
    )

    assert first.profile_version == 1
    assert second.profile_version == 2
    assert first.qualification_policy.policy_version == 1
    assert second.qualification_policy.policy_version == 2
    assert first.qualification_policy.minimum_confidence == 0.90
    assert second.qualification_policy.minimum_confidence == 0.97
    assert second.qualification_policy.minimum_evidence_count == 3
    assert second.qualification_policy.minimum_effective_sample_size == 5.0
    assert second.qualification_policy.allow_partially_achieved is True

    assert first.dimensions == second.dimensions


def test_multiple_customer_support_versions_can_coexist():
    registry = ObjectiveLearningProfileRegistry()

    first = build_customer_support_objective_learning_profile(
        profile_version=1,
        policy_version=1,
    )
    second = build_customer_support_objective_learning_profile(
        profile_version=2,
        policy_version=2,
        minimum_confidence=0.95,
    )

    returned = register_customer_support_objective_learning_profiles(
        registry,
        profiles=(first, second),
    )

    assert returned is registry
    assert registry.versions(
        namespace=CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
        objective_type=CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
    ) == (1, 2)

    assert (
        registry.get(
            namespace=CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
            objective_type=CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
        )
        is second
    )

    assert (
        registry.get(
            namespace=CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
            objective_type=CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
            profile_version=1,
        )
        is first
    )


def test_default_product_registration_registers_v1():
    registry = build_default_objective_learning_profile_registry()

    assert registry.keys() == ()

    register_customer_support_objective_learning_profiles(registry)

    assert registry.keys() == (
        (
            CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
            CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
            1,
        ),
    )


def test_product_registration_rejects_other_objective():
    registry = ObjectiveLearningProfileRegistry()

    profile = build_customer_support_objective_learning_profile().model_copy(
        update={
            "profile_ref": "another.objective",
            "objective_namespace": "another",
            "objective_type": "another",
        }
    )

    with pytest.raises(
        ValueError,
        match="another objective family",
    ):
        register_customer_support_objective_learning_profiles(
            registry,
            profiles=(profile,),
        )

    assert registry.keys() == ()


def test_invalid_dynamic_policy_value_is_rejected():
    with pytest.raises(ValidationError):
        build_customer_support_objective_learning_profile(
            profile_version=2,
            policy_version=2,
            minimum_confidence=1.1,
        )


def test_profile_is_provider_neutral():
    profile = build_customer_support_objective_learning_profile()

    serialized = profile.model_dump_json().lower()

    assert "shopify" not in serialized
    assert "refund" not in serialized
    assert "provider_constraint" in serialized


def test_profile_round_trip_preserves_product_contract():
    original = build_customer_support_objective_learning_profile(
        profile_version=3,
        policy_version=4,
        minimum_confidence=0.96,
        metadata={
            "configuration_ref": "tenant-policy-a",
        },
    )

    restored = ObjectiveLearningProfile.model_validate(original.model_dump(mode="json"))

    assert restored == original
    assert restored.metadata["configuration_ref"] == "tenant-policy-a"
