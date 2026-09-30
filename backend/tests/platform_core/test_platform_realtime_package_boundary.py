import ast
from pathlib import Path

REALTIME = Path("app/platform/realtime")


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


def test_realtime_infrastructure_lives_under_platform():
    expected = {
        "__init__.py",
        "codec.py",
        "hub.py",
        "publisher.py",
        "schemas.py",
    }

    present = {path.name for path in REALTIME.glob("*.py")}

    assert expected <= present


def test_old_top_level_realtime_package_is_gone():
    assert not Path("app/realtime").exists()


def test_platform_realtime_does_not_import_product_domains():
    for path in REALTIME.glob("*.py"):
        modules = _imports(path)

        assert not any(module.startswith("app.domains.") for module in modules), path


def test_customer_service_realtime_semantics_remain_domain_owned():
    path = Path("app/domains/customer_service/realtime/publisher.py")

    assert path.exists()

    modules = _imports(path)

    assert any(module.startswith("app.platform.realtime") for module in modules)


def test_old_realtime_import_namespace_is_absent():
    for root in (
        Path("app"),
        Path("tests"),
    ):
        for path in root.rglob("*.py"):
            modules = _imports(path)

            assert not any(
                module == "app.realtime" or module.startswith("app.realtime.")
                for module in modules
            ), path
