from __future__ import annotations

import ast
from pathlib import Path

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID,
)

from app.models.models import (
    ObjectiveLearningExperienceRecord,
)


MODEL_FILE = Path("app/models/models.py")
MIGRATION_FILE = Path(
    "migrations/versions/cap024_add_objective_learning_experiences.py"
)


def test_objective_learning_experience_table_identity():
    table = ObjectiveLearningExperienceRecord.__table__

    assert table.name == ("objective_learning_experiences")

    assert set(table.columns.keys()) == {
        "id",
        "user_id",
        "tenant_id",
        "resolution_record_id",
        "objective_namespace",
        "objective_type",
        "objective_ref",
        "objective_version",
        "schema_ref",
        "profile_ref",
        "profile_version",
        "extractor_ref",
        "extractor_version",
        "outcome_ref",
        "evaluation_ref",
        "workflow_run_id",
        "dimension_keys_json",
        "evidence_refs_json",
        "validity_scope_json",
        "experience_json",
        "informational_only",
        "authorizes_execution",
        "created_at",
    }


def test_objective_learning_experience_column_types():
    table = ObjectiveLearningExperienceRecord.__table__

    uuid_columns = {
        "id",
        "user_id",
        "resolution_record_id",
    }

    for name in uuid_columns:
        assert isinstance(
            table.c[name].type,
            UUID,
        )

    integer_columns = {
        "objective_version",
        "profile_version",
        "extractor_version",
    }

    for name in integer_columns:
        assert isinstance(
            table.c[name].type,
            Integer,
        )

    string_columns = {
        "tenant_id",
        "objective_namespace",
        "objective_type",
        "objective_ref",
        "schema_ref",
        "profile_ref",
        "extractor_ref",
        "outcome_ref",
        "evaluation_ref",
        "workflow_run_id",
    }

    for name in string_columns:
        assert isinstance(
            table.c[name].type,
            String,
        )

    json_columns = {
        "dimension_keys_json",
        "evidence_refs_json",
        "validity_scope_json",
        "experience_json",
    }

    for name in json_columns:
        assert isinstance(
            table.c[name].type,
            JSONB,
        )

    assert isinstance(
        table.c.informational_only.type,
        Boolean,
    )
    assert isinstance(
        table.c.authorizes_execution.type,
        Boolean,
    )
    assert isinstance(
        table.c.created_at.type,
        DateTime,
    )


def test_experience_snapshot_and_lineage_are_required():
    table = ObjectiveLearningExperienceRecord.__table__

    required = {
        "user_id",
        "resolution_record_id",
        "objective_namespace",
        "objective_type",
        "objective_ref",
        "objective_version",
        "schema_ref",
        "profile_ref",
        "profile_version",
        "extractor_ref",
        "extractor_version",
        "outcome_ref",
        "evaluation_ref",
        "dimension_keys_json",
        "evidence_refs_json",
        "validity_scope_json",
        "experience_json",
        "informational_only",
        "authorizes_execution",
        "created_at",
    }

    for name in required:
        assert table.c[name].nullable is False

    assert table.c.tenant_id.nullable is True
    assert table.c.workflow_run_id.nullable is True


def test_resolution_lineage_uses_restrictive_foreign_key():
    table = ObjectiveLearningExperienceRecord.__table__

    foreign_keys = list(table.c.resolution_record_id.foreign_keys)

    assert len(foreign_keys) == 1

    foreign_key = foreign_keys[0]

    assert foreign_key.target_fullname == ("objective_resolution_records.id")
    assert foreign_key.ondelete == "RESTRICT"
    assert foreign_key.constraint.name == (
        "fk_objective_learning_experiences_resolution_record"
    )


def test_semantic_extraction_identity_is_unique():
    table = ObjectiveLearningExperienceRecord.__table__

    constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.name is not None
    }

    assert constraints["uq_objective_learning_experiences_semantic_extraction"] == (
        "user_id",
        "resolution_record_id",
        "schema_ref",
        "profile_ref",
        "profile_version",
        "extractor_ref",
        "extractor_version",
    )


def test_query_indexes_match_future_retrieval_boundaries():
    table = ObjectiveLearningExperienceRecord.__table__

    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in table.indexes
    }

    assert indexes["ix_objective_learning_experiences_owner_created"] == (
        "user_id",
        "tenant_id",
        "created_at",
    )

    assert indexes["ix_objective_learning_experiences_objective_created"] == (
        "user_id",
        "objective_namespace",
        "objective_type",
        "objective_ref",
        "created_at",
    )

    assert indexes["ix_objective_learning_experiences_resolution_created"] == (
        "resolution_record_id",
        "created_at",
    )

    assert indexes["ix_objective_learning_experiences_profile_extractor"] == (
        "profile_ref",
        "profile_version",
        "extractor_ref",
        "extractor_version",
    )


def test_record_documentation_preserves_safety_boundary():
    source = MODEL_FILE.read_text(encoding="utf-8")

    tree = ast.parse(source)

    record = next(
        node
        for node in tree.body
        if (
            isinstance(node, ast.ClassDef)
            and node.name == "ObjectiveLearningExperienceRecord"
        )
    )

    documentation = ast.get_docstring(record) or ""
    normalized_documentation = " ".join(documentation.split())

    assert "append-only" in normalized_documentation
    assert "informational only" in normalized_documentation
    assert "alter ranking" in normalized_documentation
    assert "authorize execution" in normalized_documentation
    assert "bypass verification" in normalized_documentation
    assert "runtime policy" in normalized_documentation


def test_cap024_migration_contract():
    source = MIGRATION_FILE.read_text(encoding="utf-8")

    tree = ast.parse(source)

    assignments = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(
                node.targets[0],
                ast.Name,
            )
            and node.targets[0].id
            in {
                "revision",
                "down_revision",
                "TABLE",
            }
        )
    }

    assert assignments == {
        "revision": "cap024",
        "down_revision": "cap023",
        "TABLE": ("objective_learning_experiences"),
    }

    assert '"objective_resolution_records.id"' in source
    assert 'ondelete="RESTRICT"' in source
    assert "uq_objective_learning_experiences_semantic_extraction" in source
    assert "experience_json" in source
    assert "validity_scope_json" in source
    assert "dimension_keys_json" in source
    assert "evidence_refs_json" in source
    assert "informational_only" in source
    assert "authorizes_execution" in source


def test_schema_introduces_no_behavioral_wiring():
    model_source = MODEL_FILE.read_text(encoding="utf-8")
    migration_source = MIGRATION_FILE.read_text(encoding="utf-8")

    combined = (
        model_source[
            model_source.index(
                "class ObjectiveLearningExperienceRecord"
            ) : model_source.index("# Import domain models so Alembic")
        ]
        + migration_source
    )

    # Documentation may explicitly state that ranking and
    # planning authority are forbidden. Check executable calls
    # independently and permit safety wording.
    executable_forbidden = {
        "PlatformEventPublisher",
        "JobService",
        "execute(",
        "enqueue(",
        "publish(",
        "dispatch(",
        "extract_customer_support",
    }

    for value in executable_forbidden:
        assert value not in combined

    assert "planner guidance" in combined
    assert "alter ranking" in combined
