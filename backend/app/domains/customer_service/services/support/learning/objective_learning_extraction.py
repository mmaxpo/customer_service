from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
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
)
from app.runtime.objectives.learning import (
    ObjectiveLearningDimensionDefinition,
    ObjectiveLearningDimensionValue,
    ObjectiveLearningProfile,
    ObjectiveLearningValidityScope,
    ObjectiveLearningVersionRef,
)

CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXTRACTOR_REF = (
    "customer_service.support.objective_learning_extractor"
)
CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXTRACTOR_VERSION = 1

CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXPERIENCE_SCHEMA = (
    "customer_service.support.objective_learning_experience.v1"
)


class CustomerSupportObjectiveLearningSource(BaseModel):
    """
    Validated JSON-native snapshots from durable customer-support
    lineage.

    Loading records and reconstructing canonical review plans are
    deliberately outside this contract. Product loaders must supply
    the already validated durable facts to this pure extractor.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    tenant_id: str | None = None

    objective_namespace: str = Field(min_length=1)
    objective_type: str = Field(min_length=1)
    objective_ref: str = Field(min_length=1)
    objective_version: int = Field(ge=1)

    resolution_record_id: str = Field(min_length=1)
    resolution: dict[str, Any]

    review_plan_id: str = Field(min_length=1)
    review_plan: dict[str, Any]

    outcome_ref: str = Field(min_length=1)
    outcome_version: int = Field(ge=1)
    outcome: dict[str, Any]

    evaluation_ref: str = Field(min_length=1)
    evaluation_version: int = Field(ge=1)
    evaluation: dict[str, Any]

    workflow_run_id: str | None = None
    workflow_template_ref: str | None = None
    workflow_version: str | None = None

    capability_ids: tuple[str, ...] = ()
    provider_ids: tuple[str, ...] = ()
    provider_refs: tuple[str, ...] = ()

    repair_executions: tuple[dict[str, Any], ...] = ()

    evidence_refs: tuple[str, ...] = ()
    versioned_refs: tuple[
        ObjectiveLearningVersionRef,
        ...,
    ] = ()

    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source(
        self,
    ) -> "CustomerSupportObjectiveLearningSource":
        self.user_id = self.user_id.strip()

        if self.tenant_id is not None:
            self.tenant_id = self.tenant_id.strip() or None

        self.objective_namespace = self.objective_namespace.strip().lower()
        self.objective_type = self.objective_type.strip().lower()
        self.objective_ref = self.objective_ref.strip()

        self.resolution_record_id = self.resolution_record_id.strip()
        self.review_plan_id = self.review_plan_id.strip()
        self.outcome_ref = self.outcome_ref.strip()
        self.evaluation_ref = self.evaluation_ref.strip()

        for field_name in (
            "workflow_run_id",
            "workflow_template_ref",
            "workflow_version",
        ):
            value = getattr(self, field_name)

            if value is not None:
                setattr(
                    self,
                    field_name,
                    str(value).strip() or None,
                )

        if not self.user_id:
            raise ValueError("objective learning source user_id is required")

        if (
            self.objective_namespace != CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE
            or self.objective_type != CUSTOMER_SUPPORT_OBJECTIVE_TYPE
        ):
            raise ValueError(
                "objective learning source is not the customer-support objective family"
            )

        self.capability_ids = self._normalized_unique(
            self.capability_ids,
            field_name="capability_ids",
            lowercase=True,
        )
        self.provider_ids = self._normalized_unique(
            self.provider_ids,
            field_name="provider_ids",
            lowercase=True,
        )
        self.provider_refs = self._normalized_unique(
            self.provider_refs,
            field_name="provider_refs",
            lowercase=True,
        )
        self.evidence_refs = self._normalized_unique(
            self.evidence_refs,
            field_name="evidence_refs",
            lowercase=False,
        )

        self._require_snapshot_identity(
            snapshot_name="resolution",
            snapshot=self.resolution,
        )
        self._require_snapshot_identity(
            snapshot_name="outcome",
            snapshot=self.outcome,
        )
        self._require_snapshot_identity(
            snapshot_name="evaluation",
            snapshot=self.evaluation,
        )

        return self

    def _require_snapshot_identity(
        self,
        *,
        snapshot_name: str,
        snapshot: dict[str, Any],
    ) -> None:
        namespace = self._nested_string(
            snapshot,
            ("objective", "namespace"),
        ) or self._string(snapshot.get("objective_namespace"))

        objective_type = self._nested_string(
            snapshot,
            ("objective", "objective_type"),
        ) or self._string(snapshot.get("objective_type"))

        objective_ref = self._nested_string(
            snapshot,
            ("objective", "objective_ref"),
        ) or self._string(snapshot.get("objective_ref"))

        objective_version = self._nested_int(
            snapshot,
            ("objective", "objective_version"),
        )

        if objective_version is None:
            objective_version = self._integer(snapshot.get("objective_version"))

        if namespace is not None and namespace.lower() != self.objective_namespace:
            raise ValueError(
                f"{snapshot_name} objective namespace does not match source"
            )

        if objective_type is not None and objective_type.lower() != self.objective_type:
            raise ValueError(f"{snapshot_name} objective type does not match source")

        if objective_ref is not None and objective_ref != self.objective_ref:
            raise ValueError(f"{snapshot_name} objective ref does not match source")

        if (
            objective_version is not None
            and objective_version != self.objective_version
        ):
            raise ValueError(f"{snapshot_name} objective version does not match source")

    @staticmethod
    def _normalized_unique(
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
                f"objective learning source {field_name} must contain unique values"
            )

        return normalized

    @staticmethod
    def _string(value: Any) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _integer(value: Any) -> int | None:
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _nested_string(
        cls,
        payload: dict[str, Any],
        path: tuple[str, ...],
    ) -> str | None:
        value: Any = payload

        for key in path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)

        return cls._string(value)

    @classmethod
    def _nested_int(
        cls,
        payload: dict[str, Any],
        path: tuple[str, ...],
    ) -> int | None:
        value: Any = payload

        for key in path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)

        return cls._integer(value)


class CustomerSupportObjectiveLearningExperience(BaseModel):
    """
    Immutable-by-convention extracted experience.

    This is not a promoted insight and cannot influence planning or
    execution. It preserves the profile, extractor, evidence, and
    validity versions under which extraction occurred.
    """

    model_config = ConfigDict(extra="forbid")

    schema_ref: str = CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXPERIENCE_SCHEMA

    profile_ref: str = Field(min_length=1)
    profile_version: int = Field(ge=1)

    extractor_ref: str = Field(min_length=1)
    extractor_version: int = Field(ge=1)

    user_id: str = Field(min_length=1)
    objective_ref: str = Field(min_length=1)

    resolution_record_id: str = Field(min_length=1)
    outcome_ref: str = Field(min_length=1)
    evaluation_ref: str = Field(min_length=1)

    validity_scope: ObjectiveLearningValidityScope

    dimensions: tuple[
        ObjectiveLearningDimensionValue,
        ...,
    ]

    evidence_refs: tuple[str, ...] = ()

    informational_only: bool = True
    authorizes_execution: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_experience(
        self,
    ) -> "CustomerSupportObjectiveLearningExperience":
        if not self.informational_only:
            raise ValueError(
                "objective learning experience must remain informational only"
            )

        if self.authorizes_execution:
            raise ValueError("objective learning experience cannot authorize execution")

        keys = tuple(item.key for item in self.dimensions)

        if len(keys) != len(set(keys)):
            raise ValueError(
                "objective learning experience dimension keys must be unique"
            )

        return self


class CustomerSupportObjectiveLearningExtractor:
    """
    Pure deterministic customer-support experience extractor.
    """

    def extract(
        self,
        *,
        profile: ObjectiveLearningProfile,
        source: CustomerSupportObjectiveLearningSource,
    ) -> CustomerSupportObjectiveLearningExperience:
        self._require_profile(profile)

        builders = {
            REQUIRED_EVIDENCE_DIMENSION: (self._required_evidence_value),
            PLAN_STRUCTURE_DIMENSION: (self._plan_structure_value),
            PROVIDER_CONSTRAINT_DIMENSION: (self._provider_constraint_value),
            FAILURE_PATTERN_DIMENSION: (self._failure_pattern_value),
            REPAIR_STRATEGY_DIMENSION: (self._repair_strategy_value),
            VALIDITY_CONTEXT_DIMENSION: (self._validity_context_value),
        }

        values: list[ObjectiveLearningDimensionValue] = []

        for definition in profile.dimensions:
            builder = builders.get(definition.key)

            if builder is None:
                raise ValueError(
                    "customer-support extractor does not "
                    "support profile dimension: "
                    f"{definition.key}"
                )

            value = builder(
                definition=definition,
                source=source,
                profile=profile,
            )

            if value is None:
                if definition.required_for_qualification:
                    raise ValueError(
                        "required objective learning dimension "
                        "could not be extracted: "
                        f"{definition.key}"
                    )
                continue

            values.append(value)

        extracted_keys = {item.key for item in values}

        missing_policy_dimensions = tuple(
            sorted(
                set(profile.qualification_policy.required_dimension_keys)
                - extracted_keys
            )
        )

        if missing_policy_dimensions:
            raise ValueError(
                "objective learning extraction is missing "
                "policy-required dimensions: " + ", ".join(missing_policy_dimensions)
            )

        return CustomerSupportObjectiveLearningExperience(
            profile_ref=profile.profile_ref,
            profile_version=profile.profile_version,
            extractor_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXTRACTOR_REF),
            extractor_version=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXTRACTOR_VERSION),
            user_id=source.user_id,
            objective_ref=source.objective_ref,
            resolution_record_id=(source.resolution_record_id),
            outcome_ref=source.outcome_ref,
            evaluation_ref=source.evaluation_ref,
            validity_scope=self._validity_scope(
                profile=profile,
                source=source,
            ),
            dimensions=tuple(values),
            evidence_refs=source.evidence_refs,
            informational_only=True,
            authorizes_execution=False,
            metadata={
                "review_plan_id": source.review_plan_id,
                "repair_execution_count": len(source.repair_executions),
            },
        )

    @staticmethod
    def _require_profile(
        profile: ObjectiveLearningProfile,
    ) -> None:
        if (
            profile.objective_namespace != CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE
            or profile.objective_type != CUSTOMER_SUPPORT_OBJECTIVE_TYPE
        ):
            raise ValueError(
                "customer-support extractor received another objective profile"
            )

        if not profile.enabled:
            raise ValueError("customer-support objective learning profile is disabled")

    def _required_evidence_value(
        self,
        *,
        definition: ObjectiveLearningDimensionDefinition,
        source: CustomerSupportObjectiveLearningSource,
        profile: ObjectiveLearningProfile,
    ) -> ObjectiveLearningDimensionValue:
        evidence_items = self._evidence_items(source)

        if not evidence_items:
            raise ValueError("customer-support learning requires durable evidence")

        return self._value(
            definition=definition,
            confidence=self._evaluation_confidence(source),
            evidence_refs=source.evidence_refs,
            payload={
                "count": len(evidence_items),
                "items": evidence_items,
                "resolution_record_id": (source.resolution_record_id),
                "outcome_ref": source.outcome_ref,
                "evaluation_ref": (source.evaluation_ref),
            },
        )

    def _plan_structure_value(
        self,
        *,
        definition: ObjectiveLearningDimensionDefinition,
        source: CustomerSupportObjectiveLearningSource,
        profile: ObjectiveLearningProfile,
    ) -> ObjectiveLearningDimensionValue:
        operations = self._operations(source.review_plan)

        if not operations:
            raise ValueError(
                "customer-support review plan has no extractable operations"
            )

        normalized_operations = []

        for index, operation in enumerate(
            operations,
            start=1,
        ):
            normalized_operations.append(
                {
                    "sequence": self._integer(operation.get("sequence")) or index,
                    "operation_ref": self._first_string(
                        operation,
                        "operation_ref",
                        "task_ref",
                        "id",
                    ),
                    "operation_type": self._first_string(
                        operation,
                        "operation_type",
                        "action",
                        "type",
                    ),
                    "required": bool(operation.get("required", True)),
                    "capability_id": self._first_string(
                        operation,
                        "capability_id",
                    ),
                }
            )

        return self._value(
            definition=definition,
            confidence=1.0,
            evidence_refs=(f"review_plan:{source.review_plan_id}",),
            payload={
                "review_plan_id": source.review_plan_id,
                "operation_count": len(normalized_operations),
                "operations": normalized_operations,
            },
        )

    def _provider_constraint_value(
        self,
        *,
        definition: ObjectiveLearningDimensionDefinition,
        source: CustomerSupportObjectiveLearningSource,
        profile: ObjectiveLearningProfile,
    ) -> ObjectiveLearningDimensionValue | None:
        constraints: list[dict[str, Any]] = []

        for operation in self._operations(source.review_plan):
            provider_id = self._first_string(
                operation,
                "provider_id",
                "selected_provider_id",
            )
            provider_ref = self._first_string(
                operation,
                "provider_ref",
            )
            capability_id = self._first_string(
                operation,
                "capability_id",
            )

            operation_constraints = operation.get("constraints")

            if (
                provider_id is None
                and provider_ref is None
                and capability_id is None
                and not operation_constraints
            ):
                continue

            constraints.append(
                {
                    "operation_ref": (
                        self._first_string(
                            operation,
                            "operation_ref",
                            "task_ref",
                            "id",
                        )
                    ),
                    "capability_id": capability_id,
                    "provider_id": provider_id,
                    "provider_ref": provider_ref,
                    "constraints": (
                        operation_constraints
                        if isinstance(
                            operation_constraints,
                            (dict, list),
                        )
                        else None
                    ),
                }
            )

        if (
            not constraints
            and not source.capability_ids
            and not source.provider_ids
            and not source.provider_refs
        ):
            return None

        return self._value(
            definition=definition,
            confidence=1.0,
            evidence_refs=(f"review_plan:{source.review_plan_id}",),
            payload={
                "capability_ids": list(source.capability_ids),
                "provider_ids": list(source.provider_ids),
                "provider_refs": list(source.provider_refs),
                "operation_constraints": constraints,
            },
        )

    def _failure_pattern_value(
        self,
        *,
        definition: ObjectiveLearningDimensionDefinition,
        source: CustomerSupportObjectiveLearningSource,
        profile: ObjectiveLearningProfile,
    ) -> ObjectiveLearningDimensionValue | None:
        failures = []

        for operation in self._resolution_operations(source.resolution):
            status = (
                self._first_string(
                    operation,
                    "status",
                    "resolution_status",
                )
                or ""
            ).lower()

            if status not in {
                "failed",
                "pending",
                "unknown",
                "inconclusive",
                "not_executed",
            }:
                continue

            failures.append(
                {
                    "operation_ref": (
                        self._first_string(
                            operation,
                            "operation_ref",
                            "task_ref",
                            "id",
                        )
                    ),
                    "operation_type": (
                        self._first_string(
                            operation,
                            "operation_type",
                            "action",
                            "type",
                        )
                    ),
                    "status": status,
                    "reason_code": (
                        self._first_string(
                            operation,
                            "reason_code",
                        )
                    ),
                    "required": bool(operation.get("required", True)),
                    "verification_ref": (
                        self._first_string(
                            operation,
                            "verification_ref",
                        )
                    ),
                }
            )

        if not failures:
            return None

        return self._value(
            definition=definition,
            confidence=self._evaluation_confidence(source),
            evidence_refs=source.evidence_refs,
            payload={
                "count": len(failures),
                "patterns": failures,
            },
        )

    def _repair_strategy_value(
        self,
        *,
        definition: ObjectiveLearningDimensionDefinition,
        source: CustomerSupportObjectiveLearningSource,
        profile: ObjectiveLearningProfile,
    ) -> ObjectiveLearningDimensionValue | None:
        if not source.repair_executions:
            return None

        repairs = []

        for repair in source.repair_executions:
            plan = repair.get("plan_json")

            if not isinstance(plan, dict):
                plan = repair.get("plan")

            if not isinstance(plan, dict):
                plan = {}

            actions = plan.get("actions")

            repairs.append(
                {
                    "repair_execution_id": (
                        self._first_string(
                            repair,
                            "id",
                            "repair_execution_id",
                        )
                    ),
                    "repair_request_ref": (
                        self._first_string(
                            repair,
                            "repair_request_ref",
                        )
                    ),
                    "attempt_number": (self._integer(repair.get("attempt_number"))),
                    "planner_ref": (
                        self._first_string(
                            repair,
                            "planner_ref",
                        )
                    ),
                    "planner_policy_version": (
                        self._integer(repair.get("planner_policy_version"))
                    ),
                    "controlling_disposition": (
                        self._first_string(
                            repair,
                            "controlling_disposition",
                        )
                        or self._first_string(
                            plan,
                            "disposition",
                        )
                    ),
                    "status": self._first_string(
                        repair,
                        "status",
                    ),
                    "requires_human_approval": bool(
                        repair.get(
                            "requires_human_approval",
                            plan.get(
                                "human_approval_required",
                                False,
                            ),
                        )
                    ),
                    "automatic_execution_allowed": bool(
                        repair.get(
                            "automatic_execution_allowed",
                            plan.get(
                                "automatic_execution_allowed",
                                False,
                            ),
                        )
                    ),
                    "action_count": (len(actions) if isinstance(actions, list) else 0),
                }
            )

        return self._value(
            definition=definition,
            confidence=self._evaluation_confidence(source),
            evidence_refs=tuple(
                value
                for value in (
                    (
                        "repair_execution:"
                        + str(
                            self._first_string(
                                repair,
                                "id",
                                "repair_execution_id",
                            )
                        )
                    )
                    for repair in (source.repair_executions)
                    if self._first_string(
                        repair,
                        "id",
                        "repair_execution_id",
                    )
                )
            ),
            payload={
                "repair_count": len(repairs),
                "repairs": repairs,
            },
        )

    def _validity_context_value(
        self,
        *,
        definition: ObjectiveLearningDimensionDefinition,
        source: CustomerSupportObjectiveLearningSource,
        profile: ObjectiveLearningProfile,
    ) -> ObjectiveLearningDimensionValue:
        scope = self._validity_scope(
            profile=profile,
            source=source,
        )

        return self._value(
            definition=definition,
            confidence=1.0,
            evidence_refs=(
                f"resolution:{source.resolution_record_id}",
                f"evaluation:{source.evaluation_ref}",
            ),
            payload=scope.model_dump(mode="json"),
        )

    def _validity_scope(
        self,
        *,
        profile: ObjectiveLearningProfile,
        source: CustomerSupportObjectiveLearningSource,
    ) -> ObjectiveLearningValidityScope:
        versioned = list(source.versioned_refs)

        versioned.extend(
            (
                ObjectiveLearningVersionRef(
                    ref="objective_learning_profile",
                    version=str(profile.profile_version),
                ),
                ObjectiveLearningVersionRef(
                    ref=(profile.qualification_policy.policy_ref),
                    version=str(profile.qualification_policy.policy_version),
                ),
                ObjectiveLearningVersionRef(
                    ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXTRACTOR_REF),
                    version=str(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXTRACTOR_VERSION),
                ),
                ObjectiveLearningVersionRef(
                    ref="support_outcome",
                    version=str(source.outcome_version),
                ),
                ObjectiveLearningVersionRef(
                    ref="support_outcome_evaluation",
                    version=str(source.evaluation_version),
                ),
            )
        )

        deduplicated: dict[
            str,
            ObjectiveLearningVersionRef,
        ] = {}

        for item in versioned:
            existing = deduplicated.get(item.ref)

            if existing is not None and existing.version != item.version:
                raise ValueError(
                    "objective learning validity scope "
                    "contains conflicting versions for "
                    f"{item.ref}"
                )

            deduplicated[item.ref] = item

        return ObjectiveLearningValidityScope(
            tenant_id=source.tenant_id,
            objective_namespace=(source.objective_namespace),
            objective_type=source.objective_type,
            objective_version=source.objective_version,
            capability_ids=source.capability_ids,
            provider_ids=source.provider_ids,
            provider_refs=source.provider_refs,
            workflow_template_ref=(source.workflow_template_ref),
            workflow_version=source.workflow_version,
            versioned_refs=tuple(deduplicated[key] for key in sorted(deduplicated)),
            metadata={
                "objective_ref": source.objective_ref,
                "resolution_record_id": (source.resolution_record_id),
                "review_plan_id": (source.review_plan_id),
                "outcome_ref": source.outcome_ref,
                "evaluation_ref": (source.evaluation_ref),
                "workflow_run_id": (source.workflow_run_id),
            },
        )

    def _value(
        self,
        *,
        definition: ObjectiveLearningDimensionDefinition,
        confidence: float,
        evidence_refs: tuple[str, ...],
        payload: dict[str, Any],
    ) -> ObjectiveLearningDimensionValue:
        return ObjectiveLearningDimensionValue(
            key=definition.key,
            schema_ref=definition.schema_ref,
            schema_version=definition.schema_version,
            value=payload,
            evidence_refs=self._unique(evidence_refs),
            confidence=confidence,
            extractor_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXTRACTOR_REF),
            extractor_version=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXTRACTOR_VERSION),
            metadata={
                "cardinality": (definition.cardinality.value),
                "required_for_qualification": (definition.required_for_qualification),
                "advisory_only": True,
            },
        )

    def _evidence_items(
        self,
        source: CustomerSupportObjectiveLearningSource,
    ) -> list[dict[str, Any]]:
        items = []

        evaluation_evidence = source.evaluation.get(
            "evidence_json"
        ) or source.evaluation.get("evidence")

        if isinstance(evaluation_evidence, dict):
            nested = evaluation_evidence.get("items")

            if isinstance(nested, list):
                items.extend(item for item in nested if isinstance(item, dict))
            elif evaluation_evidence:
                items.append(evaluation_evidence)

        elif isinstance(evaluation_evidence, list):
            items.extend(item for item in evaluation_evidence if isinstance(item, dict))

        for ref in source.evidence_refs:
            items.append({"evidence_ref": ref})

        items.extend(
            (
                {
                    "evidence_ref": ("resolution:" + source.resolution_record_id),
                    "source_type": ("objective_resolution"),
                },
                {
                    "evidence_ref": ("outcome:" + source.outcome_ref),
                    "source_type": "support_outcome",
                },
                {
                    "evidence_ref": ("evaluation:" + source.evaluation_ref),
                    "source_type": ("support_outcome_evaluation"),
                },
            )
        )

        return items

    @staticmethod
    def _operations(
        review_plan: dict[str, Any],
    ) -> list[dict[str, Any]]:
        for key in (
            "operations",
            "planned_operations",
            "tasks",
        ):
            value = review_plan.get(key)

            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        return []

    @staticmethod
    def _resolution_operations(
        resolution: dict[str, Any],
    ) -> list[dict[str, Any]]:
        value = resolution.get("operations")

        if not isinstance(value, list):
            return []

        return [item for item in value if isinstance(item, dict)]

    @staticmethod
    def _evaluation_confidence(
        source: CustomerSupportObjectiveLearningSource,
    ) -> float:
        value = source.evaluation.get("confidence")

        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = 1.0

        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _first_string(
        payload: dict[str, Any],
        *keys: str,
    ) -> str | None:
        for key in keys:
            value = payload.get(key)

            if value is None:
                continue

            normalized = str(value).strip()

            if normalized:
                return normalized

        return None

    @staticmethod
    def _integer(value: Any) -> int | None:
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _unique(
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        seen: set[str] = set()
        output = []

        for value in values:
            normalized = str(value).strip()

            if not normalized or normalized in seen:
                continue

            seen.add(normalized)
            output.append(normalized)

        return tuple(output)


def extract_customer_support_objective_learning(
    *,
    profile: ObjectiveLearningProfile,
    source: CustomerSupportObjectiveLearningSource,
) -> CustomerSupportObjectiveLearningExperience:
    return CustomerSupportObjectiveLearningExtractor().extract(
        profile=profile,
        source=source,
    )


__all__ = [
    "CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXPERIENCE_SCHEMA",
    "CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXTRACTOR_REF",
    "CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_EXTRACTOR_VERSION",
    "CustomerSupportObjectiveLearningExperience",
    "CustomerSupportObjectiveLearningExtractor",
    "CustomerSupportObjectiveLearningSource",
    "extract_customer_support_objective_learning",
]
