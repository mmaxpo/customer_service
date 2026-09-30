from __future__ import annotations

from copy import deepcopy
import runpy
from types import SimpleNamespace

import pytest

from app.runtime.objectives.learning import (
    ObjectiveLearningAggregation,
    ObjectiveLearningAggregationPolicy,
    ObjectiveLearningAggregator,
)


def _experience(
    *,
    objective_ref: str = "review-plan-1",
    resolution_record_id: str = "resolution-1",
    outcome_ref: str = "outcome-1",
    evaluation_ref: str = "evaluation-1",
    workflow_run_id: str = "workflow-run-1",
):
    namespace = runpy.run_path(
        "tests/customer_service/objectives/"
        "test_customer_support_objective_learning_extraction.py"
    )

    source = namespace["source"]()

    source = source.model_copy(
        update={
            "objective_ref": objective_ref,
            "resolution_record_id": (resolution_record_id),
            "outcome_ref": outcome_ref,
            "evaluation_ref": evaluation_ref,
            "workflow_run_id": workflow_run_id,
            "review_plan_id": objective_ref,
        }
    )

    from app.domains.customer_service.services.support.learning.objective_learning_extraction import (
        extract_customer_support_objective_learning,
    )
    from app.domains.customer_service.services.support.learning.objective_learning_profiles import (
        build_customer_support_objective_learning_profile,
    )

    return extract_customer_support_objective_learning(
        profile=(build_customer_support_objective_learning_profile()),
        source=source,
    )


def _payload(**kwargs):
    return _experience(**kwargs).model_dump(mode="json")


def _dimension(summary, key):
    return next(item for item in summary.dimensions if item.key == key)


def test_aggregates_structural_evidence_deterministically():
    first = _payload()
    second = _payload(
        objective_ref="review-plan-2",
        resolution_record_id="resolution-2",
        outcome_ref="outcome-2",
        evaluation_ref="evaluation-2",
        workflow_run_id="workflow-run-2",
    )

    aggregator = ObjectiveLearningAggregator(
        policy=(ObjectiveLearningAggregationPolicy(minimum_effective_sample_size=1.9))
    )

    summary = aggregator.summarize(
        experiences=[
            second,
            first,
        ]
    )

    repeated = aggregator.summarize(
        experiences=[
            deepcopy(second),
            deepcopy(first),
        ]
    )

    assert isinstance(
        summary,
        ObjectiveLearningAggregation,
    )
    assert summary == repeated

    assert summary.total_experiences == 2
    assert summary.unique_objective_count == 2
    assert summary.unique_resolution_count == 2
    assert summary.unique_outcome_count == 2
    assert summary.unique_evaluation_count == 2
    assert summary.unique_workflow_run_count == 2

    assert summary.dimension_count == 6
    assert summary.total_dimension_occurrences == 12
    assert [item.key for item in summary.dimensions] == sorted(
        item.key for item in summary.dimensions
    )

    assert summary.evidence.coverage == 1.0
    assert summary.evidence.reference_occurrences["verify:lookup"] == 2
    assert summary.evidence.reference_occurrences["verify:refund"] == 2

    assert summary.evidence_sufficient is True
    assert summary.summary_confidence > 0.0
    assert summary.informational_only is True
    assert summary.authorizes_execution is False


def test_dimension_summary_reports_coverage_and_consistency():
    first = _payload()
    second = _payload(
        objective_ref="review-plan-2",
        resolution_record_id="resolution-2",
        outcome_ref="outcome-2",
        evaluation_ref="evaluation-2",
        workflow_run_id="workflow-run-2",
    )

    summary = ObjectiveLearningAggregator().summarize(
        experiences=[
            first,
            second,
        ]
    )

    plan = _dimension(
        summary,
        "plan_structure",
    )

    assert plan.occurrence_count == 2
    assert plan.experience_count == 2
    assert plan.experience_coverage == 1.0
    assert plan.average_confidence == 1.0
    assert plan.distinct_value_count == 2
    assert plan.dominant_value_occurrences == 1
    assert plan.value_consistency_ratio == 0.5
    assert plan.evidence.coverage == 1.0


def test_missing_optional_dimension_reduces_coverage():
    first = _payload()
    second = _payload(
        objective_ref="review-plan-2",
        resolution_record_id="resolution-2",
        outcome_ref="outcome-2",
        evaluation_ref="evaluation-2",
        workflow_run_id="workflow-run-2",
    )

    second["dimensions"] = [
        item for item in second["dimensions"] if item["key"] != "repair_strategy"
    ]

    summary = ObjectiveLearningAggregator().summarize(
        experiences=[
            first,
            second,
        ]
    )

    repair = _dimension(
        summary,
        "repair_strategy",
    )

    assert repair.occurrence_count == 1
    assert repair.experience_count == 2
    assert repair.experience_coverage == 0.5

    assert summary.average_dimension_coverage < 1.0


def test_supports_persisted_record_shape():
    payload = _payload()

    record = SimpleNamespace(experience_json=payload)

    summary = ObjectiveLearningAggregator().summarize(experiences=[record])

    assert summary.total_experiences == 1
    assert summary.schema_ref == (payload["schema_ref"])
    assert summary.profile_ref == (payload["profile_ref"])


def test_mixed_validity_scopes_are_rejected():
    first = _payload()
    second = _payload(
        objective_ref="review-plan-2",
        resolution_record_id="resolution-2",
        outcome_ref="outcome-2",
        evaluation_ref="evaluation-2",
        workflow_run_id="workflow-run-2",
    )

    second["validity_scope"]["workflow_version"] = "different"

    with pytest.raises(
        ValueError,
        match="exact aggregation scope",
    ):
        ObjectiveLearningAggregator().summarize(
            experiences=[
                first,
                second,
            ]
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "informational_only",
            False,
            "informational only",
        ),
        (
            "authorizes_execution",
            True,
            "cannot authorize execution",
        ),
    ],
)
def test_unsafe_experiences_are_rejected(
    field,
    value,
    message,
):
    payload = _payload()
    payload[field] = value

    with pytest.raises(
        ValueError,
        match=message,
    ):
        ObjectiveLearningAggregator().summarize(experiences=[payload])


def test_empty_input_is_rejected():
    with pytest.raises(
        ValueError,
        match="At least one",
    ):
        ObjectiveLearningAggregator().summarize(experiences=[])


def test_aggregation_does_not_mutate_inputs():
    payload = _payload()
    before = deepcopy(payload)

    ObjectiveLearningAggregator().summarize(experiences=[payload])

    assert payload == before


def test_aggregation_has_no_database_or_behavioral_wiring():
    import ast
    from pathlib import Path

    path = Path('app/runtime/objectives/learning/aggregation.py')

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imports: set[str] = set()
    bare_calls: set[str] = set()
    attribute_calls: list[tuple[str | None, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                bare_calls.add(node.func.id)
            elif isinstance(
                node.func,
                ast.Attribute,
            ):
                owner = (
                    node.func.value.id
                    if isinstance(
                        node.func.value,
                        ast.Name,
                    )
                    else None
                )
                attribute_calls.append(
                    (
                        owner,
                        node.func.attr,
                    )
                )

    assert not any(value.startswith("sqlalchemy") for value in imports)

    assert not any(
        value.startswith("app.domains.customer_service") for value in imports
    )

    forbidden_bare_calls = {
        "publish",
        "enqueue",
        "dispatch",
        "rank",
        "rerank",
        "activate",
        "authorize",
    }

    assert not (forbidden_bare_calls & bare_calls)

    forbidden_attribute_calls = {
        ("db", "commit"),
        ("db", "flush"),
        ("db", "add"),
        ("db", "execute"),
        ("session", "commit"),
        ("session", "flush"),
        ("session", "add"),
        ("session", "execute"),
        ("repository", "record"),
        ("repository", "append"),
        ("publisher", "publish"),
        ("jobs", "enqueue"),
    }

    assert not (forbidden_attribute_calls & set(attribute_calls))

    assert "summarize" in source
    assert "informational_only" in source
    assert "authorizes_execution" in source
