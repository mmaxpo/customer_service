from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class ObjectiveLearningDimensionKind(str, Enum):
    """
    Generic semantic categories for objective-learning dimensions.

    Product profiles may use these common categories or define a
    product-specific dimension key while retaining one of these
    semantic kinds.
    """

    REQUIRED_EVIDENCE = "required_evidence"
    PLAN_STRUCTURE = "plan_structure"
    PROVIDER_CONSTRAINT = "provider_constraint"
    FAILURE_PATTERN = "failure_pattern"
    REPAIR_STRATEGY = "repair_strategy"
    VALIDITY_CONTEXT = "validity_context"
    PRODUCT_DEFINED = "product_defined"


class ObjectiveLearningDimensionCardinality(str, Enum):
    SINGLE = "single"
    MULTIPLE = "multiple"


class ObjectiveLearningDimensionDefinition(BaseModel):
    """
    Versioned declaration of one extractable learning dimension.

    This describes what a product permits the generic learning
    system to extract. It does not contain learned evidence itself.
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    kind: ObjectiveLearningDimensionKind

    schema_ref: str = Field(min_length=1)
    schema_version: int = Field(ge=1)

    cardinality: ObjectiveLearningDimensionCardinality = (
        ObjectiveLearningDimensionCardinality.SINGLE
    )

    required_for_qualification: bool = False
    advisory_only: bool = True

    description: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_definition(
        self,
    ) -> "ObjectiveLearningDimensionDefinition":
        self.key = self.key.strip().lower()
        self.schema_ref = self.schema_ref.strip().lower()
        self.description = self.description.strip()

        if not self.key:
            raise ValueError("objective learning dimension key is required")

        if not self.schema_ref:
            raise ValueError("objective learning dimension schema_ref is required")

        if not self.description:
            raise ValueError("objective learning dimension description is required")

        if not self.advisory_only:
            raise ValueError("objective learning dimensions must remain advisory only")

        return self


class ObjectiveLearningDimensionValue(BaseModel):
    """
    Immutable-by-convention extracted value for one profile dimension.

    profile_ref and profile_version identify the exact extraction
    contract that produced this value. The payload remains typed by
    schema_ref and schema_version rather than by product-specific
    fields in the generic runtime.
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)

    schema_ref: str = Field(min_length=1)
    schema_version: int = Field(ge=1)

    value: dict[str, Any]

    evidence_refs: tuple[str, ...] = ()
    confidence: float = Field(ge=0.0, le=1.0)

    extractor_ref: str = Field(min_length=1)
    extractor_version: int = Field(ge=1)

    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_value(
        self,
    ) -> "ObjectiveLearningDimensionValue":
        self.key = self.key.strip().lower()
        self.schema_ref = self.schema_ref.strip().lower()
        self.extractor_ref = self.extractor_ref.strip().lower()

        if not self.key:
            raise ValueError("objective learning dimension value key is required")

        if not self.schema_ref:
            raise ValueError(
                "objective learning dimension value schema_ref is required"
            )

        if not self.extractor_ref:
            raise ValueError("objective learning dimension extractor_ref is required")

        normalized_evidence = tuple(
            value
            for value in (str(item).strip() for item in self.evidence_refs)
            if value
        )

        if len(normalized_evidence) != len(set(normalized_evidence)):
            raise ValueError("objective learning evidence refs must be unique")

        self.evidence_refs = normalized_evidence
        return self


class ObjectiveLearningVersionRef(BaseModel):
    """
    Generic reference to a versioned policy, provider, workflow,
    capability, planner, runtime, or other provenance component.
    """

    model_config = ConfigDict(extra="forbid")

    ref: str = Field(min_length=1)
    version: str = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_ref(
        self,
    ) -> "ObjectiveLearningVersionRef":
        self.ref = self.ref.strip().lower()
        self.version = self.version.strip()

        if not self.ref:
            raise ValueError("objective learning version ref is required")

        if not self.version:
            raise ValueError("objective learning version is required")

        return self


class ObjectiveLearningValidityScope(BaseModel):
    """
    Provenance and compatibility boundary for learned experience.

    Fields are intentionally explicit for common indexed identities,
    while versioned_refs allows future products to add policy and
    system version dimensions without changing this contract.
    """

    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = None

    objective_namespace: str = Field(min_length=1)
    objective_type: str = Field(min_length=1)
    objective_version: int | None = Field(default=None, ge=1)

    capability_ids: tuple[str, ...] = ()
    provider_ids: tuple[str, ...] = ()
    provider_refs: tuple[str, ...] = ()

    workflow_template_ref: str | None = None
    workflow_version: str | None = None

    planner_ref: str | None = None
    planner_policy_version: str | None = None

    versioned_refs: tuple[ObjectiveLearningVersionRef, ...] = ()

    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_scope(
        self,
    ) -> "ObjectiveLearningValidityScope":
        if self.tenant_id is not None:
            normalized_tenant = self.tenant_id.strip()
            self.tenant_id = normalized_tenant or None

        self.objective_namespace = self.objective_namespace.strip().lower()
        self.objective_type = self.objective_type.strip().lower()

        if not self.objective_namespace:
            raise ValueError("objective learning namespace is required")

        if not self.objective_type:
            raise ValueError("objective learning objective_type is required")

        self.capability_ids = self._normalize_unique(
            self.capability_ids,
            field_name="capability_ids",
            lowercase=True,
        )
        self.provider_ids = self._normalize_unique(
            self.provider_ids,
            field_name="provider_ids",
            lowercase=True,
        )
        self.provider_refs = self._normalize_unique(
            self.provider_refs,
            field_name="provider_refs",
            lowercase=True,
        )

        for field_name in (
            "workflow_template_ref",
            "workflow_version",
            "planner_ref",
            "planner_policy_version",
        ):
            value = getattr(self, field_name)

            if value is None:
                continue

            normalized = str(value).strip()

            setattr(
                self,
                field_name,
                normalized or None,
            )

        version_keys = tuple(item.ref for item in self.versioned_refs)

        if len(version_keys) != len(set(version_keys)):
            raise ValueError("objective learning versioned refs must have unique refs")

        return self

    @staticmethod
    def _normalize_unique(
        values: tuple[str, ...],
        *,
        field_name: str,
        lowercase: bool,
    ) -> tuple[str, ...]:
        normalized = tuple(
            value
            for value in (
                (str(item).strip().lower() if lowercase else str(item).strip())
                for item in values
            )
            if value
        )

        if len(normalized) != len(set(normalized)):
            raise ValueError(
                f"objective learning {field_name} must contain unique values"
            )

        return normalized


class ObjectiveLearningQualificationPolicy(BaseModel):
    """
    Versioned policy controlling whether objective evidence is safe
    and sufficient to become a learning candidate.

    This policy qualifies evidence only. It never authorizes planner
    or execution influence.
    """

    model_config = ConfigDict(extra="forbid")

    policy_ref: str = Field(min_length=1)
    policy_version: int = Field(ge=1)

    require_terminal_resolution: bool = True
    require_verification: bool = True

    allow_achieved: bool = True
    allow_partially_achieved: bool = False
    allow_repaired_achievement: bool = True

    minimum_confidence: float = Field(
        default=0.90,
        ge=0.0,
        le=1.0,
    )
    minimum_evidence_count: int = Field(
        default=1,
        ge=0,
    )
    minimum_evidence_coverage: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )
    minimum_effective_sample_size: float = Field(
        default=1.0,
        gt=0.0,
    )
    maximum_contradiction_score: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
    )
    minimum_stability_score: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
    )

    required_dimension_keys: tuple[str, ...] = ()

    explicit_approval_required: bool = True
    informational_only: bool = True

    affects_ranking: bool = False
    affects_capability_selection: bool = False
    affects_business_plan: bool = False
    selects_provider: bool = False
    authorizes_execution: bool = False
    bypasses_approval: bool = False
    bypasses_verification: bool = False

    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_policy(
        self,
    ) -> "ObjectiveLearningQualificationPolicy":
        self.policy_ref = self.policy_ref.strip().lower()

        if not self.policy_ref:
            raise ValueError("objective learning policy_ref is required")

        self.required_dimension_keys = tuple(
            value
            for value in (
                str(item).strip().lower() for item in self.required_dimension_keys
            )
            if value
        )

        if len(self.required_dimension_keys) != len(set(self.required_dimension_keys)):
            raise ValueError("required objective learning dimensions must be unique")

        if not (
            self.allow_achieved
            or self.allow_partially_achieved
            or self.allow_repaired_achievement
        ):
            raise ValueError(
                "objective learning policy must allow at least one qualifying outcome"
            )

        if not self.informational_only:
            raise ValueError("objective learning must remain informational only")

        forbidden_influence = (
            self.affects_ranking,
            self.affects_capability_selection,
            self.affects_business_plan,
            self.selects_provider,
            self.authorizes_execution,
            self.bypasses_approval,
            self.bypasses_verification,
        )

        if any(forbidden_influence):
            raise ValueError(
                "objective learning policy cannot alter planning or execution decisions"
            )

        return self


class ObjectiveLearningProfile(BaseModel):
    """
    Versioned product-neutral declaration of what may be learned
    for one objective family.

    Product composition roots own profile registration. Core runtime
    contains no customer-service, refund, Shopify, or other
    product-specific assumptions.
    """

    model_config = ConfigDict(extra="forbid")

    profile_ref: str = Field(min_length=1)
    profile_version: int = Field(ge=1)

    objective_namespace: str = Field(min_length=1)
    objective_type: str = Field(min_length=1)

    dimensions: tuple[
        ObjectiveLearningDimensionDefinition,
        ...,
    ]

    qualification_policy: ObjectiveLearningQualificationPolicy

    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_profile(
        self,
    ) -> "ObjectiveLearningProfile":
        self.profile_ref = self.profile_ref.strip().lower()
        self.objective_namespace = self.objective_namespace.strip().lower()
        self.objective_type = self.objective_type.strip().lower()

        if not self.profile_ref:
            raise ValueError("objective learning profile_ref is required")

        if not self.objective_namespace:
            raise ValueError("objective learning profile namespace is required")

        if not self.objective_type:
            raise ValueError("objective learning profile objective_type is required")

        if not self.dimensions:
            raise ValueError(
                "objective learning profile requires at least one dimension"
            )

        dimension_keys = tuple(item.key for item in self.dimensions)

        if len(dimension_keys) != len(set(dimension_keys)):
            raise ValueError("objective learning profile dimension keys must be unique")

        known_dimensions = set(dimension_keys)
        required_dimensions = set(self.qualification_policy.required_dimension_keys)

        missing = tuple(sorted(required_dimensions - known_dimensions))

        if missing:
            raise ValueError(
                "objective learning policy requires "
                "undefined profile dimensions: " + ", ".join(missing)
            )

        return self


__all__ = [
    "ObjectiveLearningDimensionCardinality",
    "ObjectiveLearningDimensionDefinition",
    "ObjectiveLearningDimensionKind",
    "ObjectiveLearningDimensionValue",
    "ObjectiveLearningProfile",
    "ObjectiveLearningQualificationPolicy",
    "ObjectiveLearningValidityScope",
    "ObjectiveLearningVersionRef",
]
