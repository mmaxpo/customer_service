import ast
from pathlib import Path

SCHEDULES = Path("app/platform/schedules")


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


def test_schedule_infrastructure_lives_under_platform():
    assert SCHEDULES.exists()

    expected = {
        "__init__.py",
        "repository.py",
        "scheduler.py",
        "schemas.py",
        "service.py",
    }

    present = {path.name for path in SCHEDULES.glob("*.py")}

    assert expected <= present


def test_old_top_level_schedule_package_is_gone():
    assert not Path("app/schedules").exists()


def test_platform_schedules_do_not_import_product_domains():
    for path in SCHEDULES.glob("*.py"):
        modules = _imports(path)

        assert not any(module.startswith("app.domains.") for module in modules), path


def test_scheduler_enqueues_through_platform_jobs():
    modules = _imports(Path("app/platform/schedules/scheduler.py"))

    assert "app.platform.jobs.service" in modules


def test_old_schedule_import_namespace_is_absent():
    for root in (
        Path("app"),
        Path("tests"),
    ):
        for path in root.rglob("*.py"):
            modules = _imports(path)

            assert not any(
                module == "app.schedules" or module.startswith("app.schedules.")
                for module in modules
            ), path
