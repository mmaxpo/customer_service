from __future__ import annotations

import ast
from pathlib import Path

from app.runtime.engine.executor import (
    execute_workflow_dag as EngineExecuteWorkflow,
)
from app.runtime.engine.persistence.postgres import (
    PostgresEventSink,
    PostgresRunStore,
)
from app.runtime.engine.persistence.types import (
    EventSink as EngineEventSink,
    RunStore as EngineRunStore,
)
from app.runtime.engine.workflow_repo_postgres import (
    PostgresWorkflowRepo,
)
from app.runtime.engine.validator import (
    ValidationError as EngineValidationError,
)
from app.runtime.engine.validator import (
    validate_workflow as EngineValidateWorkflow,
)
from app.runtime.execution import (
    execute_workflow_dag,
)
from app.runtime.persistence import (
    EventSink,
    RunStore,
    build_event_sink,
    build_run_store,
)
from app.runtime.validation import (
    ValidationError,
    validate_workflow,
)
from app.runtime.workflows import (
    RuntimeWorkflowRepository,
    build_runtime_workflow_repository,
)


def test_runtime_public_boundaries_preserve_core_identity():
    assert execute_workflow_dag is EngineExecuteWorkflow

    assert validate_workflow is EngineValidateWorkflow
    assert ValidationError is EngineValidationError

    assert RunStore is EngineRunStore
    assert EventSink is EngineEventSink


def test_runtime_event_sink_factory_owns_concrete_adapter():
    db = object()

    sink = build_event_sink(db)  # type: ignore[arg-type]

    assert isinstance(sink, PostgresEventSink)
    assert sink.db is db


def test_runtime_run_store_factory_owns_concrete_adapter():
    db = object()

    store = build_run_store(db)  # type: ignore[arg-type]

    assert isinstance(store, PostgresRunStore)
    assert store.db is db


def test_runtime_workflow_repository_factory_owns_concrete_adapter():
    db = object()

    repository = build_runtime_workflow_repository(
        db  # type: ignore[arg-type]
    )

    assert isinstance(
        repository,
        PostgresWorkflowRepo,
    )
    assert repository.db is db


def test_runtime_workflow_repository_contract_shape():
    names = {
        name
        for name in (
            "create",
            "get",
            "list",
            "update",
            "delete",
        )
        if hasattr(
            RuntimeWorkflowRepository,
            name,
        )
    }

    assert names == {
        "create",
        "get",
        "list",
        "update",
        "delete",
    }


def test_customer_service_does_not_import_runtime_engine_internals():
    root = Path("app/domains/customer_service")

    violations: list[tuple[str, int, str]] = []

    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())

        for node in ast.walk(tree):
            modules: list[str] = []

            if isinstance(
                node,
                ast.ImportFrom,
            ):
                modules.append(node.module or "")

            elif isinstance(
                node,
                ast.Import,
            ):
                modules.extend(alias.name for alias in node.names)

            for module in modules:
                if module.startswith("app.runtime.engine"):
                    violations.append(
                        (
                            str(path),
                            node.lineno,
                            module,
                        )
                    )

    assert violations == []


def test_shopify_provider_uses_public_runtime_extensions_only():
    allowed = {
        "app.runtime.resources",
        "app.runtime.nodes.registry",
    }

    violations: list[tuple[str, int, str]] = []

    for path in Path("app/providers/shopify").rglob("*.py"):
        tree = ast.parse(path.read_text())

        for node in ast.walk(tree):
            if not isinstance(
                node,
                ast.ImportFrom,
            ):
                continue

            module = node.module or ""

            if module.startswith("app.runtime") and module not in allowed:
                violations.append(
                    (
                        str(path),
                        node.lineno,
                        module,
                    )
                )

    assert violations == []
