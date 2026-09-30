from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.runtime.objectives.learning import (
    ObjectiveLearningDimensionCardinality,
    ObjectiveLearningDimensionDefinition,
    ObjectiveLearningDimensionKind,
    ObjectiveLearningDimensionValue,
    ObjectiveLearningProfile,
    ObjectiveLearningQualificationPolicy,
    ObjectiveLearningValidityScope,
    ObjectiveLearningVersionRef,
)


def dimension(
    *,
    key: str = "required_evidence",
    kind=(ObjectiveLearningDimensionKind.REQUIRED_EVIDENCE),
    required: bool = True,
):
    return ObjectiveLearningDimensionDefinition(
        key=key,
        kind=kind,
        schema_ref=(f"objective_learning.dimension.{key}.v1"),
        schema_version=1,
        cardinality=(ObjectiveLearningDimensionCardinality.MULTIPLE),
        required_for_qualification=required,
        advisory_only=True,
        description=f"Extract {key}.",
    )


def policy(
    *,
    required_dimension_keys=("required_evidence",),
    **updates,
):
    values = {
        "policy_ref": ("objective_learning.policy.default"),
        "policy_version": 1,
        "required_dimension_keys": (required_dimension_keys),
    }
    values.update(updates)

    return ObjectiveLearningQualificationPolicy(**values)


def profile(
    *,
    version: int = 1,
    dimensions=None,
    qualification_policy=None,
):
    return ObjectiveLearningProfile(
        profile_ref=("customer_service.support.multi_operation"),
        profile_version=version,
        objective_namespace=("customer_service.support"),
        objective_type="multi_operation",
        dimensions=(
            dimensions
            if dimensions is not None
            else (
                dimension(),
                dimension(
                    key="repair_strategy",
                    kind=(ObjectiveLearningDimensionKind.REPAIR_STRATEGY),
                    required=False,
                ),
            )
        ),
        qualification_policy=(
            qualification_policy if qualification_policy is not None else policy()
        ),
    )


def test_dimension_definition_normalizes_identity():
    item = ObjectiveLearningDimensionDefinition(
        key=" Required_Evidence ",
        kind=(ObjectiveLearningDimensionKind.REQUIRED_EVIDENCE),
        schema_ref=(" Objective_Learning.Dimension.Evidence.V1 "),
        schema_version=1,
        description=" Evidence needed. ",
    )

    assert item.key == "required_evidence"
    assert item.schema_ref == ("objective_learning.dimension.evidence.v1")
    assert item.description == "Evidence needed."
    assert item.advisory_only is True


def test_dimension_value_preserves_typed_payload_and_evidence():
    item = ObjectiveLearningDimensionValue(
        key=" Provider_Constraint ",
        schema_ref=("Objective_Learning.Dimension.Provider_Constraint.V1"),
        schema_version=1,
        value={
            "provider_id": "shopify",
            "constraints": [
                "order_must_be_refundable",
            ],
        },
        evidence_refs=(
            "event:1",
            "verification:1",
        ),
        confidence=0.95,
        extractor_ref=("Customer_Service.Support.Extractor"),
        extractor_version=1,
    )

    assert item.key == "provider_constraint"
    assert item.extractor_ref == ("customer_service.support.extractor")
    assert item.evidence_refs == (
        "event:1",
        "verification:1",
    )
    assert item.value["provider_id"] == "shopify"


def test_dimension_value_rejects_duplicate_evidence():
    with pytest.raises(
        ValidationError,
        match="evidence refs must be unique",
    ):
        ObjectiveLearningDimensionValue(
            key="failure_pattern",
            schema_ref=("objective_learning.dimension.failure_pattern.v1"),
            schema_version=1,
            value={"reason_code": "timeout"},
            evidence_refs=("event:1", "event:1"),
            confidence=0.8,
            extractor_ref="test.extractor",
            extractor_version=1,
        )


def test_validity_scope_normalizes_common_identifiers():
    scope = ObjectiveLearningValidityScope(
        tenant_id=" tenant-a ",
        objective_namespace=(" Customer_Service.Support "),
        objective_type=" MULTI_OPERATION ",
        objective_version=3,
        capability_ids=(
            " Ecommerce.Orders.Get ",
            "Ecommerce.Orders.Refund",
        ),
        provider_ids=(" Shopify ",),
        provider_refs=(" Shopify.Order_Action ",),
        workflow_template_ref=" workflow-1 ",
        workflow_version=" 4 ",
        planner_ref=" repair-planner ",
        planner_policy_version=" 2 ",
        versioned_refs=(
            ObjectiveLearningVersionRef(
                ref=" Refund_Policy ",
                version=" v3 ",
            ),
            ObjectiveLearningVersionRef(
                ref=" Provider_API ",
                version=" 2026-07 ",
            ),
        ),
    )

    assert scope.tenant_id == "tenant-a"
    assert scope.objective_namespace == ("customer_service.support")
    assert scope.objective_type == "multi_operation"
    assert scope.capability_ids == (
        "ecommerce.orders.get",
        "ecommerce.orders.refund",
    )
    assert scope.provider_ids == ("shopify",)
    assert scope.provider_refs == ("shopify.order_action",)
    assert scope.workflow_version == "4"
    assert scope.versioned_refs[0].ref == ("refund_policy")


def test_validity_scope_rejects_duplicate_versions():
    with pytest.raises(
        ValidationError,
        match="unique refs",
    ):
        ObjectiveLearningValidityScope(
            objective_namespace="example",
            objective_type="test",
            versioned_refs=(
                ObjectiveLearningVersionRef(
                    ref="policy",
                    version="1",
                ),
                ObjectiveLearningVersionRef(
                    ref="POLICY",
                    version="2",
                ),
            ),
        )


@pytest.mark.parametrize(
    "update",
    [
        {"informational_only": False},
        {"affects_ranking": True},
        {
            "affects_capability_selection": True,
        },
        {"affects_business_plan": True},
        {"selects_provider": True},
        {"authorizes_execution": True},
        {"bypasses_approval": True},
        {"bypasses_verification": True},
    ],
)
def test_policy_rejects_decision_influence(update):
    with pytest.raises(
        ValidationError,
        match=("informational only|cannot alter"),
    ):
        policy(**update)


def test_policy_is_dynamic_but_safely_bounded():
    item = policy(
        minimum_confidence=0.97,
        minimum_evidence_count=3,
        minimum_evidence_coverage=0.90,
        minimum_effective_sample_size=7.5,
        maximum_contradiction_score=0.10,
        minimum_stability_score=0.95,
        allow_partially_achieved=True,
    )

    assert item.minimum_confidence == 0.97
    assert item.minimum_evidence_count == 3
    assert item.minimum_effective_sample_size == 7.5
    assert item.allow_partially_achieved is True
    assert item.explicit_approval_required is True
    assert item.informational_only is True


def test_profile_requires_unique_dimensions():
    with pytest.raises(
        ValidationError,
        match="dimension keys must be unique",
    ):
        profile(
            dimensions=(
                dimension(),
                dimension(),
            )
        )


def test_profile_rejects_undefined_required_dimension():
    with pytest.raises(
        ValidationError,
        match="undefined profile dimensions",
    ):
        profile(
            qualification_policy=policy(required_dimension_keys=("missing_dimension",))
        )


def test_profile_allows_product_defined_dimension():
    item = profile(
        dimensions=(
            dimension(
                key="refund_eligibility_context",
                kind=(ObjectiveLearningDimensionKind.PRODUCT_DEFINED),
            ),
        ),
        qualification_policy=policy(
            required_dimension_keys=("refund_eligibility_context",)
        ),
    )

    assert item.dimensions[0].kind == (ObjectiveLearningDimensionKind.PRODUCT_DEFINED)
    assert item.qualification_policy.required_dimension_keys == (
        "refund_eligibility_context",
    )


def test_profile_serialization_is_deterministic():
    item = profile()

    payload = item.model_dump(mode="json")
    restored = ObjectiveLearningProfile.model_validate(payload)

    assert restored == item
