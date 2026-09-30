import ast
from pathlib import Path

WEBHOOKS = Path("app/platform/webhooks")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    result: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                result.add(node.module)

        elif isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)

    return result


def test_webhook_infrastructure_lives_under_platform():
    expected = {
        "__init__.py",
        "repository.py",
        "schemas.py",
        "service.py",
    }

    present = {path.name for path in WEBHOOKS.glob("*.py")}

    assert expected <= present


def test_old_top_level_webhook_package_is_gone():
    assert not Path("app/webhooks").exists()


def test_platform_webhooks_do_not_import_product_domains():
    for path in WEBHOOKS.rglob("*.py"):
        modules = _imports(path)

        assert not any(module.startswith("app.domains.") for module in modules), path


def test_platform_provider_registry_is_generic():
    path = Path("app/platform/webhooks/providers/registry.py")

    modules = _imports(path)

    assert not any(
        module.startswith("app.domains.") or module.startswith("app.providers.")
        for module in modules
    )


def test_shopify_webhook_adapter_is_shopify_owned():
    path = Path("app/domains/customer_service/integrations/shopify/webhooks.py")

    assert path.exists()

    modules = _imports(path)

    assert "app.platform.webhooks.providers.base" in modules


def test_stripe_webhook_adapter_is_provider_owned():
    path = Path("app/providers/stripe/webhooks.py")

    assert path.exists()

    modules = _imports(path)

    assert "app.platform.webhooks.providers.base" in modules


def test_application_composition_wires_provider_adapters():
    text = Path("app/platform/composition.py").read_text()

    assert "build_default_webhook_provider_registry" in text

    assert "ShopifyWebhookAdapter" in text
    assert "StripeWebhookAdapter" in text


def test_old_webhook_namespace_is_absent():
    for root in (
        Path("app"),
        Path("tests"),
    ):
        for path in root.rglob("*.py"):
            modules = _imports(path)

            assert not any(
                module == "app.webhooks" or module.startswith("app.webhooks.")
                for module in modules
            ), path
