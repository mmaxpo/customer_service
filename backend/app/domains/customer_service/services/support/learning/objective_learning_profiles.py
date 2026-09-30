from __future__ import annotations

from typing import Any

from app.runtime.objectives.learning import (
    ObjectiveLearningDimensionCardinality,
    ObjectiveLearningDimensionDefinition,
    ObjectiveLearningDimensionKind,
    ObjectiveLearningProfile,
    ObjectiveLearningProfileRegistry,
    ObjectiveLearningQualificationPolicy,
)

CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE = "customer_service.support"
CUSTOMER_SUPPORT_OBJECTIVE_TYPE = "multi_operation"

CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF = (
    "customer_service.support.multi_operation"
)
CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_VERSION = 1

CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF = (
    "customer_service.support.objective_learning"
)
CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_VERSION = 1

REQUIRED_EVIDENCE_DIMENSION = "required_evidence"
PLAN_STRUCTURE_DIMENSION = "plan_structure"
PROVIDER_CONSTRAINT_DIMENSION = "provider_constraint"
FAILURE_PATTERN_DIMENSION = "failure_pattern"
REPAIR_STRATEGY_DIMENSION = "repair_strategy"
VALIDITY_CONTEXT_DIMENSION = "validity_context"

CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_DIMENSIONS = (
    REQUIRED_EVIDENCE_DIMENSION,
    PLAN_STRUCTURE_DIMENSION,
    PROVIDER_CONSTRAINT_DIMENSION,
    FAILURE_PATTERN_DIMENSION,
    REPAIR_STRATEGY_DIMENSION,
    VALIDITY_CONTEXT_DIMENSION,
)


def build_customer_support_objective_learning_profile(
    *,
    profile_version: int = (CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_VERSION),
    policy_version: int = (CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_VERSION),
    minimum_confidence: float = 0.90,
    minimum_evidence_count: int = 1,
    minimum_evidence_coverage: float = 1.0,
    minimum_effective_sample_size: float = 1.0,
    maximum_contradiction_score: float = 0.20,
    minimum_stability_score: float = 0.80,
    allow_partially_achieved: bool = False,
    allow_repaired_achievement: bool = True,
    explicit_approval_required: bool = True,
    enabled: bool = True,
    metadata: dict[str, Any] | None = None,
) -> ObjectiveLearningProfile:
    """
    Build one versioned customer-support learning profile.

    Product composition owns the dimensions and qualification
    thresholds. Generic objective learning remains unaware of
    customer-service and provider-specific semantics.

    Policy changes must produce new profile and policy versions so
    historical evidence retains the interpretation under which it
    qualified.
    """

    return ObjectiveLearningProfile(
        profile_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF),
        profile_version=profile_version,
        objective_namespace=(CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE),
        objective_type=CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
        dimensions=_customer_support_dimensions(),
        qualification_policy=(
            ObjectiveLearningQualificationPolicy(
                policy_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF),
                policy_version=policy_version,
                require_terminal_resolution=True,
                require_verification=True,
                allow_achieved=True,
                allow_partially_achieved=(allow_partially_achieved),
                allow_repaired_achievement=(allow_repaired_achievement),
                minimum_confidence=minimum_confidence,
                minimum_evidence_count=(minimum_evidence_count),
                minimum_evidence_coverage=(minimum_evidence_coverage),
                minimum_effective_sample_size=(minimum_effective_sample_size),
                maximum_contradiction_score=(maximum_contradiction_score),
                minimum_stability_score=(minimum_stability_score),
                required_dimension_keys=(
                    REQUIRED_EVIDENCE_DIMENSION,
                    PLAN_STRUCTURE_DIMENSION,
                    VALIDITY_CONTEXT_DIMENSION,
                ),
                explicit_approval_required=(explicit_approval_required),
                informational_only=True,
                affects_ranking=False,
                affects_capability_selection=False,
                affects_business_plan=False,
                selects_provider=False,
                authorizes_execution=False,
                bypasses_approval=False,
                bypasses_verification=False,
                metadata={
                    "product": "customer_service",
                    "objective_family": (CUSTOMER_SUPPORT_OBJECTIVE_TYPE),
                },
            )
        ),
        enabled=enabled,
        metadata={
            "product": "customer_service",
            "domain": "customer_support",
            **dict(metadata or {}),
        },
    )


def register_customer_support_objective_learning_profiles(
    registry: ObjectiveLearningProfileRegistry,
    *,
    profiles: tuple[ObjectiveLearningProfile, ...] | None = None,
) -> ObjectiveLearningProfileRegistry:
    """
    Register customer-support profiles into an explicitly supplied
    product-neutral registry.

    Core defaults remain empty. Product composition chooses which
    versions are registered.
    """

    resolved_profiles = (
        profiles
        if profiles is not None
        else (build_customer_support_objective_learning_profile(),)
    )

    for profile in resolved_profiles:
        _require_customer_support_profile(profile)
        registry.register(profile)

    return registry


def _customer_support_dimensions() -> tuple[ObjectiveLearningDimensionDefinition, ...]:
    return (
        ObjectiveLearningDimensionDefinition(
            key=REQUIRED_EVIDENCE_DIMENSION,
            kind=(ObjectiveLearningDimensionKind.REQUIRED_EVIDENCE),
            schema_ref=("customer_service.objective_learning.required_evidence.v1"),
            schema_version=1,
            cardinality=(ObjectiveLearningDimensionCardinality.MULTIPLE),
            required_for_qualification=True,
            advisory_only=True,
            description=(
                "Evidence types and relationships necessary to "
                "verify the customer-support objective."
            ),
            metadata={
                "source_families": [
                    "objective_resolution",
                    "task_verification",
                    "support_outcome_evaluation",
                ],
            },
        ),
        ObjectiveLearningDimensionDefinition(
            key=PLAN_STRUCTURE_DIMENSION,
            kind=ObjectiveLearningDimensionKind.PLAN_STRUCTURE,
            schema_ref=("customer_service.objective_learning.plan_structure.v1"),
            schema_version=1,
            cardinality=(ObjectiveLearningDimensionCardinality.SINGLE),
            required_for_qualification=True,
            advisory_only=True,
            description=(
                "The ordered customer-support operation structure "
                "associated with the proven business result."
            ),
            metadata={
                "preserve_order": True,
                "include_required_flags": True,
            },
        ),
        ObjectiveLearningDimensionDefinition(
            key=PROVIDER_CONSTRAINT_DIMENSION,
            kind=(ObjectiveLearningDimensionKind.PROVIDER_CONSTRAINT),
            schema_ref=("customer_service.objective_learning.provider_constraint.v1"),
            schema_version=1,
            cardinality=(ObjectiveLearningDimensionCardinality.MULTIPLE),
            required_for_qualification=False,
            advisory_only=True,
            description=(
                "Provider, capability, installation, and external "
                "business constraints that affected execution or "
                "verification."
            ),
            metadata={
                "provider_neutral": True,
                "provider_specific_assumptions": False,
            },
        ),
        ObjectiveLearningDimensionDefinition(
            key=FAILURE_PATTERN_DIMENSION,
            kind=ObjectiveLearningDimensionKind.FAILURE_PATTERN,
            schema_ref=("customer_service.objective_learning.failure_pattern.v1"),
            schema_version=1,
            cardinality=(ObjectiveLearningDimensionCardinality.MULTIPLE),
            required_for_qualification=False,
            advisory_only=True,
            description=(
                "Failed, pending, unknown, unsupported, or "
                "inconclusive operation patterns observed before "
                "the final customer-support result."
            ),
            metadata={
                "include_reason_codes": True,
                "include_operation_status": True,
            },
        ),
        ObjectiveLearningDimensionDefinition(
            key=REPAIR_STRATEGY_DIMENSION,
            kind=ObjectiveLearningDimensionKind.REPAIR_STRATEGY,
            schema_ref=("customer_service.objective_learning.repair_strategy.v1"),
            schema_version=1,
            cardinality=(ObjectiveLearningDimensionCardinality.MULTIPLE),
            required_for_qualification=False,
            advisory_only=True,
            description=(
                "Repair dispositions, actions, approvals, waits, "
                "and replanning steps associated with eventual "
                "objective achievement."
            ),
            metadata={
                "include_attempt_number": True,
                "include_controlling_disposition": True,
                "include_human_approval": True,
            },
        ),
        ObjectiveLearningDimensionDefinition(
            key=VALIDITY_CONTEXT_DIMENSION,
            kind=ObjectiveLearningDimensionKind.VALIDITY_CONTEXT,
            schema_ref=("customer_service.objective_learning.validity_context.v1"),
            schema_version=1,
            cardinality=(ObjectiveLearningDimensionCardinality.SINGLE),
            required_for_qualification=True,
            advisory_only=True,
            description=(
                "Tenant, objective, capability, provider, policy, "
                "planner, workflow, and schema versions under "
                "which the learned result was valid."
            ),
            metadata={
                "tenant_scope_required": True,
                "version_lineage_required": True,
            },
        ),
    )


def _require_customer_support_profile(
    profile: ObjectiveLearningProfile,
) -> None:
    if (
        profile.profile_ref != CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF
        or profile.objective_namespace != CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE
        or profile.objective_type != CUSTOMER_SUPPORT_OBJECTIVE_TYPE
    ):
        raise ValueError(
            "customer-support objective-learning composition "
            "received a profile for another objective family"
        )


__all__ = [
    "CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_DIMENSIONS",
    "CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF",
    "CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_VERSION",
    "CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF",
    "CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_VERSION",
    "CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE",
    "CUSTOMER_SUPPORT_OBJECTIVE_TYPE",
    "FAILURE_PATTERN_DIMENSION",
    "PLAN_STRUCTURE_DIMENSION",
    "PROVIDER_CONSTRAINT_DIMENSION",
    "REPAIR_STRATEGY_DIMENSION",
    "REQUIRED_EVIDENCE_DIMENSION",
    "VALIDITY_CONTEXT_DIMENSION",
    "build_customer_support_objective_learning_profile",
    "register_customer_support_objective_learning_profiles",
]
