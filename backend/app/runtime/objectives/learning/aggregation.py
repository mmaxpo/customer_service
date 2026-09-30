from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from copy import deepcopy
from hashlib import sha256
import json
from math import prod
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ObjectiveLearningEvidenceSummary(BaseModel):
    """
    Deterministic summary of evidence references.

    References are counted but not interpreted. Evidence presence
    contributes to advisory aggregation confidence only.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    experience_count: int = Field(ge=0)
    experiences_with_evidence: int = Field(ge=0)
    total_reference_occurrences: int = Field(ge=0)
    unique_reference_count: int = Field(ge=0)

    coverage: float = Field(
        ge=0.0,
        le=1.0,
    )

    references: tuple[str, ...] = ()
    reference_occurrences: dict[str, int] = Field(default_factory=dict)


class ObjectiveLearningDimensionSummary(BaseModel):
    """
    Structural summary of one learning dimension.

    Values are compared only through canonical fingerprints. The
    generic aggregator does not understand product-owned value
    semantics and does not treat a dominant value as an instruction.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    key: str
    schema_refs: tuple[str, ...]
    schema_versions: tuple[int, ...]
    extractor_refs: tuple[str, ...]
    extractor_versions: tuple[int, ...]

    occurrence_count: int = Field(ge=0)
    experience_count: int = Field(ge=0)

    experience_coverage: float = Field(
        ge=0.0,
        le=1.0,
    )
    average_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    distinct_value_count: int = Field(ge=0)
    dominant_value_occurrences: int = Field(ge=0)
    value_consistency_ratio: float = Field(
        ge=0.0,
        le=1.0,
    )

    evidence: ObjectiveLearningEvidenceSummary


class ObjectiveLearningAggregation(BaseModel):
    """
    Advisory aggregation over immutable learning experiences.

    The aggregation reports repeated structural evidence within one
    exact validity scope. It does not modify planning, ranking,
    provider selection, workflow execution, or runtime policy.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    schema_ref: str
    profile_ref: str
    profile_version: int = Field(ge=1)
    extractor_ref: str
    extractor_version: int = Field(ge=1)

    tenant_id: str | None = None
    objective_namespace: str
    objective_type: str
    objective_version: int = Field(ge=1)

    validity_scope: dict[str, Any]
    scope_fingerprint: str

    total_experiences: int = Field(ge=1)
    unique_objective_count: int = Field(ge=0)
    unique_resolution_count: int = Field(ge=0)
    unique_outcome_count: int = Field(ge=0)
    unique_evaluation_count: int = Field(ge=0)
    unique_workflow_run_count: int = Field(ge=0)

    total_dimension_occurrences: int = Field(ge=0)
    dimension_count: int = Field(ge=0)
    dimensions: tuple[
        ObjectiveLearningDimensionSummary,
        ...,
    ]

    evidence: ObjectiveLearningEvidenceSummary

    average_dimension_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )
    average_dimension_coverage: float = Field(
        ge=0.0,
        le=1.0,
    )

    effective_sample_size: float = Field(ge=0.0)
    minimum_effective_sample_size: float = Field(ge=0.1)
    evidence_sufficient: bool

    summary_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    informational_only: bool = True
    authorizes_execution: bool = False


class ObjectiveLearningAggregationPolicy:
    """
    Deterministic policy for structural experience aggregation.

    Confidence combines:
      1. average dimension confidence,
      2. global evidence coverage,
      3. average dimension coverage,
      4. effective sample size.

    The policy performs no product interpretation and applies no
    time decay. Query windows belong to the later read-service slice.
    """

    def __init__(
        self,
        *,
        minimum_effective_sample_size: float = 3.0,
        missing_evidence_weight: float = 0.75,
    ) -> None:
        if minimum_effective_sample_size <= 0.0:
            raise ValueError("minimum_effective_sample_size must be > 0")

        if not 0.0 <= missing_evidence_weight <= 1.0:
            raise ValueError("missing_evidence_weight must be between 0 and 1")

        self.minimum_effective_sample_size = float(minimum_effective_sample_size)
        self.missing_evidence_weight = float(missing_evidence_weight)


class ObjectiveLearningAggregator:
    """
    Pure deterministic aggregation over experience snapshots.

    Inputs may be:
      - persisted records exposing ``experience_json``;
      - mappings containing ``experience_json``;
      - direct serialized experience mappings;
      - Pydantic experience models exposing ``model_dump``.

    Every experience must belong to the same exact validity scope and
    extraction contract. Mixed scopes are rejected instead of being
    silently generalized.
    """

    def __init__(
        self,
        *,
        policy: (ObjectiveLearningAggregationPolicy | None) = None,
    ) -> None:
        self.policy = policy or ObjectiveLearningAggregationPolicy()

    def summarize(
        self,
        *,
        experiences: Iterable[Any],
    ) -> ObjectiveLearningAggregation:
        payloads = [_experience_payload(item) for item in experiences]

        if not payloads:
            raise ValueError("At least one objective learning experience is required")

        for payload in payloads:
            _validate_safety(payload)

        expected_identity = objective_learning_aggregation_key(payloads[0])

        for payload in payloads[1:]:
            identity = objective_learning_aggregation_key(payload)

            if identity != expected_identity:
                raise ValueError(
                    "Objective learning experiences "
                    "must share one exact aggregation "
                    "scope"
                )

        total = len(payloads)
        validity_scope = deepcopy(payloads[0]["validity_scope"])

        dimensions_by_key: dict[
            str,
            list[dict[str, Any]],
        ] = defaultdict(list)

        total_dimension_occurrences = 0
        all_dimension_confidences: list[float] = []

        for payload in payloads:
            seen_keys: set[str] = set()

            for raw_dimension in payload["dimensions"]:
                dimension = dict(raw_dimension)
                key = _required_string(
                    dimension.get("key"),
                    field_name="dimension key",
                )

                if key in seen_keys:
                    raise ValueError(
                        f"One experience cannot contain duplicate dimension key: {key}"
                    )

                seen_keys.add(key)
                dimensions_by_key[key].append(dimension)
                total_dimension_occurrences += 1
                all_dimension_confidences.append(
                    _bounded_float(
                        dimension.get(
                            "confidence",
                            0.0,
                        )
                    )
                )

        dimension_summaries = tuple(
            self._summarize_dimension(
                key=key,
                dimensions=dimensions_by_key[key],
                total_experiences=total,
            )
            for key in sorted(dimensions_by_key)
        )

        evidence = _evidence_summary(
            references_by_experience=[
                payload.get("evidence_refs") or [] for payload in payloads
            ]
        )

        average_dimension_confidence = (
            sum(all_dimension_confidences) / len(all_dimension_confidences)
            if all_dimension_confidences
            else 0.0
        )

        average_dimension_coverage = (
            sum(dimension.experience_coverage for dimension in dimension_summaries)
            / len(dimension_summaries)
            if dimension_summaries
            else 0.0
        )

        experience_weights = [self._experience_weight(payload) for payload in payloads]
        effective_sample_size = sum(experience_weights)

        sample_confidence = min(
            effective_sample_size / (self.policy.minimum_effective_sample_size),
            1.0,
        )

        quality_signals = (
            _bounded_float(average_dimension_confidence),
            evidence.coverage,
            _bounded_float(average_dimension_coverage),
            sample_confidence,
        )

        quality_product = prod(quality_signals)

        summary_confidence = quality_product**0.25 if quality_product > 0.0 else 0.0

        evidence_sufficient = effective_sample_size >= (
            self.policy.minimum_effective_sample_size
        )

        first = payloads[0]

        workflow_refs = {
            workflow_run_id
            for payload in payloads
            if (workflow_run_id := _workflow_run_id(payload))
        }

        return ObjectiveLearningAggregation(
            schema_ref=_required_string(
                first.get("schema_ref"),
                field_name="schema_ref",
            ),
            profile_ref=_required_string(
                first.get("profile_ref"),
                field_name="profile_ref",
            ),
            profile_version=_positive_int(
                first.get("profile_version"),
                field_name="profile_version",
            ),
            extractor_ref=_required_string(
                first.get("extractor_ref"),
                field_name="extractor_ref",
            ),
            extractor_version=_positive_int(
                first.get("extractor_version"),
                field_name="extractor_version",
            ),
            tenant_id=_optional_string(validity_scope.get("tenant_id")),
            objective_namespace=_required_string(
                validity_scope.get("objective_namespace"),
                field_name="objective_namespace",
            ),
            objective_type=_required_string(
                validity_scope.get("objective_type"),
                field_name="objective_type",
            ),
            objective_version=_positive_int(
                validity_scope.get("objective_version"),
                field_name="objective_version",
            ),
            validity_scope=validity_scope,
            scope_fingerprint=expected_identity,
            total_experiences=total,
            unique_objective_count=len(
                {
                    _required_string(
                        payload.get("objective_ref"),
                        field_name=("objective_ref"),
                    )
                    for payload in payloads
                }
            ),
            unique_resolution_count=len(
                {
                    _required_string(
                        payload.get("resolution_record_id"),
                        field_name=("resolution_record_id"),
                    )
                    for payload in payloads
                }
            ),
            unique_outcome_count=len(
                {
                    _required_string(
                        payload.get("outcome_ref"),
                        field_name="outcome_ref",
                    )
                    for payload in payloads
                }
            ),
            unique_evaluation_count=len(
                {
                    _required_string(
                        payload.get("evaluation_ref"),
                        field_name=("evaluation_ref"),
                    )
                    for payload in payloads
                }
            ),
            unique_workflow_run_count=len(workflow_refs),
            total_dimension_occurrences=(total_dimension_occurrences),
            dimension_count=len(dimension_summaries),
            dimensions=dimension_summaries,
            evidence=evidence,
            average_dimension_confidence=(_bounded_float(average_dimension_confidence)),
            average_dimension_coverage=(_bounded_float(average_dimension_coverage)),
            effective_sample_size=(effective_sample_size),
            minimum_effective_sample_size=(self.policy.minimum_effective_sample_size),
            evidence_sufficient=(evidence_sufficient),
            summary_confidence=(_bounded_float(summary_confidence)),
            informational_only=True,
            authorizes_execution=False,
        )

    def _summarize_dimension(
        self,
        *,
        key: str,
        dimensions: list[dict[str, Any]],
        total_experiences: int,
    ) -> ObjectiveLearningDimensionSummary:
        confidences = [
            _bounded_float(
                dimension.get(
                    "confidence",
                    0.0,
                )
            )
            for dimension in dimensions
        ]

        fingerprints = Counter(
            _fingerprint(dimension.get("value")) for dimension in dimensions
        )

        dominant_value_occurrences = max(fingerprints.values()) if fingerprints else 0

        occurrence_count = len(dimensions)

        return ObjectiveLearningDimensionSummary(
            key=key,
            schema_refs=tuple(
                sorted(
                    {
                        _required_string(
                            dimension.get("schema_ref"),
                            field_name=("dimension schema_ref"),
                        )
                        for dimension in dimensions
                    }
                )
            ),
            schema_versions=tuple(
                sorted(
                    {
                        _positive_int(
                            dimension.get("schema_version"),
                            field_name=("dimension schema_version"),
                        )
                        for dimension in dimensions
                    }
                )
            ),
            extractor_refs=tuple(
                sorted(
                    {
                        _required_string(
                            dimension.get("extractor_ref"),
                            field_name=("dimension extractor_ref"),
                        )
                        for dimension in dimensions
                    }
                )
            ),
            extractor_versions=tuple(
                sorted(
                    {
                        _positive_int(
                            dimension.get("extractor_version"),
                            field_name=("dimension extractor_version"),
                        )
                        for dimension in dimensions
                    }
                )
            ),
            occurrence_count=occurrence_count,
            experience_count=total_experiences,
            experience_coverage=(occurrence_count / total_experiences),
            average_confidence=(
                _bounded_float(sum(confidences) / occurrence_count)
                if occurrence_count
                else 0.0
            ),
            distinct_value_count=len(fingerprints),
            dominant_value_occurrences=(dominant_value_occurrences),
            value_consistency_ratio=(
                dominant_value_occurrences / occurrence_count
                if occurrence_count
                else 0.0
            ),
            evidence=_evidence_summary(
                references_by_experience=[
                    dimension.get("evidence_refs") or [] for dimension in dimensions
                ]
            ),
        )

    def _experience_weight(
        self,
        payload: dict[str, Any],
    ) -> float:
        dimensions = list(payload.get("dimensions") or [])

        average_confidence = (
            sum(
                _bounded_float(
                    dimension.get(
                        "confidence",
                        0.0,
                    )
                )
                for dimension in dimensions
            )
            / len(dimensions)
            if dimensions
            else 0.0
        )

        evidence_weight = (
            1.0
            if payload.get("evidence_refs")
            else (self.policy.missing_evidence_weight)
        )

        return average_confidence * evidence_weight


def _experience_payload(
    value: Any,
) -> dict[str, Any]:
    if isinstance(value, Mapping):
        raw = value.get("experience_json") if "experience_json" in value else value
    elif hasattr(value, "experience_json"):
        raw = getattr(
            value,
            "experience_json",
        )
    elif hasattr(value, "model_dump"):
        raw = value.model_dump(mode="json")
    else:
        raise TypeError(
            "Objective learning experience must "
            "be a mapping, persisted record, or "
            "Pydantic model"
        )

    if not isinstance(raw, Mapping):
        raise TypeError("Objective learning experience payload must be a mapping")

    payload = deepcopy(dict(raw))

    if not payload:
        raise ValueError("Objective learning experience payload must not be empty")

    if not isinstance(
        payload.get("validity_scope"),
        Mapping,
    ):
        raise ValueError("validity_scope must be a mapping")

    if not isinstance(
        payload.get("dimensions"),
        list,
    ):
        raise ValueError("dimensions must be a list")

    return payload


def _validate_safety(
    payload: dict[str, Any],
) -> None:
    if payload.get("informational_only") is not True:
        raise ValueError(
            "Objective learning experiences must remain informational only"
        )

    if payload.get("authorizes_execution") is not False:
        raise ValueError("Objective learning experiences cannot authorize execution")


def objective_learning_aggregation_key(
    value: Any,
) -> str:
    """
    Return the canonical exact-scope aggregation key.

    Instance-specific validity metadata is intentionally excluded.
    Extraction contract and all reusable validity constraints remain
    part of the key.
    """

    payload = _experience_payload(value)

    return _fingerprint({key: item for key, item in _aggregation_identity(payload)})


def _aggregation_identity(
    payload: dict[str, Any],
) -> tuple[tuple[str, Any], ...]:
    scope = dict(payload["validity_scope"])

    scope_without_instance_metadata = {
        key: deepcopy(value) for key, value in scope.items() if key != "metadata"
    }

    return (
        (
            "schema_ref",
            _required_string(
                payload.get("schema_ref"),
                field_name="schema_ref",
            ),
        ),
        (
            "profile_ref",
            _required_string(
                payload.get("profile_ref"),
                field_name="profile_ref",
            ),
        ),
        (
            "profile_version",
            _positive_int(
                payload.get("profile_version"),
                field_name="profile_version",
            ),
        ),
        (
            "extractor_ref",
            _required_string(
                payload.get("extractor_ref"),
                field_name="extractor_ref",
            ),
        ),
        (
            "extractor_version",
            _positive_int(
                payload.get("extractor_version"),
                field_name="extractor_version",
            ),
        ),
        (
            "validity_scope",
            scope_without_instance_metadata,
        ),
    )


def _workflow_run_id(
    payload: dict[str, Any],
) -> str | None:
    scope = dict(payload.get("validity_scope") or {})
    metadata = dict(scope.get("metadata") or {})

    return _optional_string(metadata.get("workflow_run_id"))


def _evidence_summary(
    *,
    references_by_experience: Iterable[Iterable[Any]],
) -> ObjectiveLearningEvidenceSummary:
    groups = [
        tuple(
            _required_string(
                reference,
                field_name="evidence reference",
            )
            for reference in references
        )
        for references in references_by_experience
    ]

    counts = Counter(reference for group in groups for reference in group)

    experience_count = len(groups)
    experiences_with_evidence = sum(1 for group in groups if group)

    references = tuple(sorted(counts))

    return ObjectiveLearningEvidenceSummary(
        experience_count=experience_count,
        experiences_with_evidence=(experiences_with_evidence),
        total_reference_occurrences=sum(counts.values()),
        unique_reference_count=len(references),
        coverage=(
            experiences_with_evidence / experience_count if experience_count else 0.0
        ),
        references=references,
        reference_occurrences={
            reference: counts[reference] for reference in references
        },
    )


def _fingerprint(
    value: Any,
) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )

    return sha256(canonical.encode("utf-8")).hexdigest()


def _required_string(
    value: Any,
    *,
    field_name: str,
) -> str:
    normalized = str(value).strip()

    if not normalized:
        raise ValueError(f"{field_name} must not be empty")

    return normalized


def _optional_string(
    value: Any | None,
) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip()

    return normalized or None


def _positive_int(
    value: Any,
    *,
    field_name: str,
) -> int:
    try:
        normalized = int(value)
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc

    if normalized < 1:
        raise ValueError(f"{field_name} must be >= 1")

    return normalized


def _bounded_float(
    value: Any,
) -> float:
    resolved = float(value)

    if resolved <= 0.0:
        return 0.0

    if resolved >= 1.0:
        return 1.0

    return resolved


__all__ = [
    "ObjectiveLearningAggregation",
    "ObjectiveLearningAggregationPolicy",
    "ObjectiveLearningAggregator",
    "ObjectiveLearningDimensionSummary",
    "ObjectiveLearningEvidenceSummary",
    "objective_learning_aggregation_key",
]
