import ast
from pathlib import Path


def _imports(path: str) -> set[str]:
    tree = ast.parse(Path(path).read_text())

    result: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                result.add(node.module)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                result.add(alias.name)

    return result


def test_event_registry_is_generic_and_has_no_composition_side_effect():
    path = "app/platform/events/registry.py"
    modules = _imports(path)
    text = Path(path).read_text()

    assert not any(module.startswith("app.domains.") for module in modules)

    assert "app.platform.composition" not in modules

    assert "register_default_event_handlers(" not in text


def test_job_registry_is_generic_and_has_no_composition_side_effect():
    path = "app/platform/jobs/handlers.py"
    modules = _imports(path)
    text = Path(path).read_text()

    assert not any(module.startswith("app.domains.") for module in modules)

    assert "app.platform.composition" not in modules

    assert "register_default_job_handlers(" not in text


def test_event_bus_builds_application_default_at_runtime_boundary():
    text = Path("app/platform/events/event_bus.py").read_text()

    assert "build_default_event_registry" in text


def test_job_worker_builds_application_default_at_runtime_boundary():
    path = "app/platform/jobs/worker.py"
    modules = _imports(path)
    text = Path(path).read_text()

    assert "build_default_job_registry" in text

    assert not any(
        module.startswith("app.domains.customer_service") for module in modules
    )

    assert "CustomerServiceRealtimePublisher" not in text


def test_platform_composition_connects_application_handlers():
    text = Path("app/platform/composition.py").read_text()

    for name in (
        "register_customer_service_event_handlers",
        "register_customer_service_job_handlers",
        "register_customer_service_omnichannel_job_handlers",
        "register_capability_event_handlers",
        "register_capability_job_handlers",
        "register_workflow_event_handlers",
        "register_workflow_job_handlers",
    ):
        assert name in text


def test_customer_service_event_behavior_is_domain_owned():
    path = Path("app/domains/customer_service/events/handlers.py")

    assert path.exists()

    text = path.read_text()

    assert "register_customer_service_event_handlers" in text

    assert "publish_customer_service_workflow_job_realtime" in text


def test_customer_service_job_behavior_is_domain_owned():
    path = Path("app/domains/customer_service/jobs/handlers.py")

    assert path.exists()

    assert "register_customer_service_job_handlers" in path.read_text()
