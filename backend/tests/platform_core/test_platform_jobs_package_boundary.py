import ast
from pathlib import Path

PLATFORM_JOBS = Path("app/platform/jobs")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())

    result: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                result.add(node.module)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                result.add(alias.name)

    return result


def test_generic_job_infrastructure_lives_under_platform():
    expected = {
        "__init__.py",
        "__main__.py",
        "contracts.py",
        "dead_letter.py",
        "dead_letter_schemas.py",
        "handlers.py",
        "lease.py",
        "metrics.py",
        "recovery.py",
        "replay.py",
        "repository.py",
        "retry.py",
        "runner.py",
        "schemas.py",
        "service.py",
        "worker.py",
    }

    present = {path.name for path in PLATFORM_JOBS.glob("*.py")}

    assert expected <= present


def test_old_top_level_jobs_package_is_gone():
    assert not Path("app/jobs").exists()


def test_platform_jobs_do_not_import_product_domains():
    for path in PLATFORM_JOBS.glob("*.py"):
        modules = _imports(path)

        assert not any(module.startswith("app.domains.") for module in modules), path


def test_workflow_job_behavior_is_runtime_owned():
    path = Path("app/runtime/workflow_jobs.py")

    assert path.exists()

    text = path.read_text()

    assert "register_workflow_job_handlers" in text

    assert "execute_workflow_dag" in text


def test_capability_job_behavior_is_capability_owned():
    path = Path("app/runtime/capabilities/execution/jobs.py")

    assert path.exists()

    assert "register_capability_job_handlers" in path.read_text()


def test_capability_maintenance_is_capability_health_owned():
    path = Path("app/runtime/capabilities/execution/health/maintenance.py")

    assert path.exists()

    assert "CapabilityHealthMaintenanceTicker" in path.read_text()


def test_platform_composition_connects_job_owners():
    text = Path("app/platform/composition.py").read_text()

    assert "app.platform.jobs.handlers" in text

    assert "app.runtime.workflow_jobs" in text

    assert "app.runtime.capabilities.execution.jobs" in text
