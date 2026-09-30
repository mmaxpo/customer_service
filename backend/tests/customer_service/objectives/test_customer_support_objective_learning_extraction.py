from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.domains.customer_service.services.support.learning.objective_learning_extraction import (
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXTRACTOR_REF,
    CustomerSupportObjectiveLearningExperience,
    CustomerSupportObjectiveLearningExtractor,
    CustomerSupportObjectiveLearningSource,
    extract_customer_support_objective_learning,
)
from app.domains.customer_service.services.support.learning.objective_learning_profiles import (
    CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
    CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
    FAILURE_PATTERN_DIMENSION,
    PLAN_STRUCTURE_DIMENSION,
    PROVIDER_CONSTRAINT_DIMENSION,
    REPAIR_STRATEGY_DIMENSION,
    REQUIRED_EVIDENCE_DIMENSION,
    VALIDITY_CONTEXT_DIMENSION,
    build_customer_support_objective_learning_profile,
)


def source(
    *,
    repair: bool = True,
    failures: bool = True,
    provider: bool = True,
) -> CustomerSupportObjectiveLearningSource:
    resolution_operations = [
        {
            "operation_ref": "lookup-order",
            "operation_type": "order_lookup",
            "status": "achieved",
            "reason_code": "order_found",
            "required": True,
            "verification_ref": "verify:lookup",
        },
        {
            "operation_ref": "refund-order",
            "operation_type": "order_action",
            "status": ("failed" if failures else "achieved"),
            "reason_code": ("provider_rejected" if failures else "refund_confirmed"),
            "required": True,
            "verification_ref": "verify:refund",
        },
    ]

    review_operations = [
        {
            "sequence": 1,
            "operation_ref": "lookup-order",
            "operation_type": "order_lookup",
            "required": True,
            "capability_id": "ecommerce.orders.get",
            **(
                {
                    "provider_id": "commerce-provider",
                    "provider_ref": ("commerce-provider.order_read"),
                }
                if provider
                else {}
            ),
        },
        {
            "sequence": 2,
            "operation_ref": "refund-order",
            "operation_type": "order_action",
            "required": True,
            "capability_id": ("ecommerce.orders.manage"),
            "constraints": {
                "requires_approval": True,
                "order_must_be_refundable": True,
            },
            **(
                {
                    "provider_id": "commerce-provider",
                    "provider_ref": ("commerce-provider.order_action"),
                }
                if provider
                else {}
            ),
        },
    ]

    repairs = (
        (
            {
                "id": "repair-1",
                "repair_request_ref": "repair-request-1",
                "attempt_number": 1,
                "planner_ref": ("customer_support.repair_planner"),
                "planner_policy_version": 1,
                "controlling_disposition": ("replan_remaining"),
                "status": "succeeded",
                "requires_human_approval": True,
                "automatic_execution_allowed": False,
                "plan_json": {
                    "disposition": ("replan_remaining"),
                    "actions": [
                        {
                            "action_ref": "action-1",
                            "target_operation_refs": ["refund-order"],
                        }
                    ],
                },
            },
        )
        if repair
        else ()
    )

    return CustomerSupportObjectiveLearningSource(
        user_id="user-1",
        tenant_id="tenant-1",
        objective_namespace=(CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE),
        objective_type=(CUSTOMER_SUPPORT_OBJECTIVE_TYPE),
        objective_ref="review-plan-1",
        objective_version=1,
        resolution_record_id="resolution-1",
        resolution={
            "objective": {
                "namespace": (CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE),
                "objective_type": (CUSTOMER_SUPPORT_OBJECTIVE_TYPE),
                "objective_ref": "review-plan-1",
                "objective_version": 1,
            },
            "status": ("achieved" if not failures else "partially_achieved"),
            "operations": resolution_operations,
            "evidence_refs": [
                "verify:lookup",
                "verify:refund",
            ],
        },
        review_plan_id="review-plan-1",
        review_plan={
            "review_plan_id": "review-plan-1",
            "operations": review_operations,
        },
        outcome_ref="outcome-1",
        outcome_version=1,
        outcome={
            "objective_namespace": (CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE),
            "objective_type": (CUSTOMER_SUPPORT_OBJECTIVE_TYPE),
            "objective_ref": "review-plan-1",
            "objective_version": 1,
            "result": ("achieved" if not failures else "partially_achieved"),
        },
        evaluation_ref="evaluation-1",
        evaluation_version=1,
        evaluation={
            "objective_namespace": (CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE),
            "objective_type": (CUSTOMER_SUPPORT_OBJECTIVE_TYPE),
            "objective_ref": "review-plan-1",
            "objective_version": 1,
            "confidence": 0.96,
            "evidence_json": {
                "items": [
                    {
                        "evidence_ref": ("provider-state:refund"),
                        "source_type": ("provider_confirmation"),
                    }
                ]
            },
        },
        workflow_run_id="workflow-run-1",
        workflow_template_ref=("customer-support-review"),
        workflow_version="4",
        capability_ids=(
            "ecommerce.orders.get",
            "ecommerce.orders.manage",
        ),
        provider_ids=(("commerce-provider",) if provider else ()),
        provider_refs=(
            (
                "commerce-provider.order_read",
                "commerce-provider.order_action",
            )
            if provider
            else ()
        ),
        repair_executions=repairs,
        evidence_refs=(
            "verify:lookup",
            "verify:refund",
        ),
    )


def dimensions(experience):
    return {item.key: item for item in experience.dimensions}


def test_extracts_all_available_profile_dimensions():
    profile = build_customer_support_objective_learning_profile()

    experience = extract_customer_support_objective_learning(
        profile=profile,
        source=source(),
    )

    by_key = dimensions(experience)

    assert tuple(by_key) == (
        REQUIRED_EVIDENCE_DIMENSION,
        PLAN_STRUCTURE_DIMENSION,
        PROVIDER_CONSTRAINT_DIMENSION,
        FAILURE_PATTERN_DIMENSION,
        REPAIR_STRATEGY_DIMENSION,
        VALIDITY_CONTEXT_DIMENSION,
    )

    assert experience.profile_ref == (profile.profile_ref)
    assert experience.profile_version == 1
    assert experience.extractor_ref == (
        CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXTRACTOR_REF
    )
    assert experience.informational_only is True
    assert experience.authorizes_execution is False


def test_plan_structure_preserves_operation_order():
    experience = CustomerSupportObjectiveLearningExtractor().extract(
        profile=(build_customer_support_objective_learning_profile()),
        source=source(),
    )

    plan = dimensions(experience)[PLAN_STRUCTURE_DIMENSION].value

    assert plan["operation_count"] == 2
    assert [item["operation_ref"] for item in plan["operations"]] == [
        "lookup-order",
        "refund-order",
    ]
    assert [item["sequence"] for item in plan["operations"]] == [1, 2]


def test_provider_constraint_is_provider_neutral():
    experience = extract_customer_support_objective_learning(
        profile=(build_customer_support_objective_learning_profile()),
        source=source(),
    )

    provider = dimensions(experience)[PROVIDER_CONSTRAINT_DIMENSION].value

    assert provider["provider_ids"] == ["commerce-provider"]
    assert provider["capability_ids"] == [
        "ecommerce.orders.get",
        "ecommerce.orders.manage",
    ]

    serialized = experience.model_dump_json().lower()

    assert "shopify" not in serialized


def test_failure_pattern_is_absent_when_no_failure():
    experience = extract_customer_support_objective_learning(
        profile=(build_customer_support_objective_learning_profile()),
        source=source(failures=False),
    )

    assert FAILURE_PATTERN_DIMENSION not in (dimensions(experience))


def test_repair_strategy_is_absent_without_repairs():
    experience = extract_customer_support_objective_learning(
        profile=(build_customer_support_objective_learning_profile()),
        source=source(repair=False),
    )

    assert REPAIR_STRATEGY_DIMENSION not in (dimensions(experience))


def test_optional_provider_dimension_can_be_absent():
    original = source(provider=False)

    review_plan = {
        **original.review_plan,
        "operations": [
            {
                key: value
                for key, value in operation.items()
                if key
                not in {
                    "capability_id",
                    "provider_id",
                    "provider_ref",
                    "selected_provider_id",
                    "constraints",
                }
            }
            for operation in original.review_plan["operations"]
        ],
    }

    item = original.model_copy(
        update={
            "review_plan": review_plan,
            "capability_ids": (),
            "provider_ids": (),
            "provider_refs": (),
        }
    )

    experience = extract_customer_support_objective_learning(
        profile=(build_customer_support_objective_learning_profile()),
        source=item,
    )

    assert PROVIDER_CONSTRAINT_DIMENSION not in (dimensions(experience))


def test_validity_scope_preserves_versions():
    profile = build_customer_support_objective_learning_profile(
        profile_version=3,
        policy_version=4,
    )

    experience = extract_customer_support_objective_learning(
        profile=profile,
        source=source(),
    )

    scope = experience.validity_scope

    assert scope.tenant_id == "tenant-1"
    assert scope.objective_version == 1
    assert scope.workflow_version == "4"

    versions = {item.ref: item.version for item in scope.versioned_refs}

    assert versions["objective_learning_profile"] == "3"
    assert versions[profile.qualification_policy.policy_ref] == "4"
    assert versions[CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXTRACTOR_REF] == "1"
    assert versions["support_outcome"] == "1"
    assert versions["support_outcome_evaluation"] == "1"


def test_extraction_is_deterministic_and_json_stable():
    profile = build_customer_support_objective_learning_profile()
    item = source()

    first = extract_customer_support_objective_learning(
        profile=profile,
        source=item,
    )
    second = extract_customer_support_objective_learning(
        profile=profile,
        source=deepcopy(item),
    )

    assert first == second

    restored = CustomerSupportObjectiveLearningExperience.model_validate(
        first.model_dump(mode="json")
    )

    assert restored == first


def test_source_rejects_mismatched_objective_lineage():
    payload = source().model_dump(mode="json")
    payload["evaluation"]["objective_ref"] = "another-objective"

    with pytest.raises(
        ValidationError,
        match="evaluation objective ref",
    ):
        CustomerSupportObjectiveLearningSource(**payload)


def test_disabled_profile_cannot_extract():
    profile = build_customer_support_objective_learning_profile(enabled=False)

    with pytest.raises(
        ValueError,
        match="profile is disabled",
    ):
        extract_customer_support_objective_learning(
            profile=profile,
            source=source(),
        )


def test_required_evidence_cannot_be_empty():
    item = source().model_copy(
        update={
            "evidence_refs": (),
            "evaluation": {
                **source().evaluation,
                "evidence_json": {},
            },
        }
    )

    # Durable resolution, outcome, and evaluation references are
    # themselves evidence, so extraction remains valid.
    experience = extract_customer_support_objective_learning(
        profile=(build_customer_support_objective_learning_profile()),
        source=item,
    )

    evidence = dimensions(experience)[REQUIRED_EVIDENCE_DIMENSION]

    assert evidence.value["count"] == 3


def test_extractor_has_no_input_mutation():
    profile = build_customer_support_objective_learning_profile()
    item = source()

    profile_before = profile.model_dump(mode="json")
    source_before = item.model_dump(mode="json")

    extract_customer_support_objective_learning(
        profile=profile,
        source=item,
    )

    assert profile.model_dump(mode="json") == (profile_before)
    assert item.model_dump(mode="json") == (source_before)
