from app.core.config import settings
from app.domains.customer_service.integrations.shopify.provider_factory import (
    ShopifyProviderFactory,
)
from app.domains.customer_service.integrations.shopify.real_provider import (
    RealShopifyProvider,
)
from app.domains.customer_service.providers.shopify import (
    FakeShopifyProvider,
)


def clear(monkeypatch):
    for name in (
        "PYTEST_CURRENT_TEST",
        "SHOPIFY_USE_REAL_PROVIDER",
        "APP_ENV",
        "ENVIRONMENT",
    ):
        monkeypatch.delenv(
            name,
            raising=False,
        )

    # Isolate the factory contract from values loaded from
    # the developer's real local .env at module import time.
    monkeypatch.setattr(
        settings,
        "SHOPIFY_USE_REAL_PROVIDER",
        False,
    )


def test_pytest_fake(
    monkeypatch,
):
    monkeypatch.setenv(
        "PYTEST_CURRENT_TEST",
        "test",
    )

    assert isinstance(
        ShopifyProviderFactory.create(),
        FakeShopifyProvider,
    )


def test_development_defaults_fake(
    monkeypatch,
):
    clear(monkeypatch)
    monkeypatch.setenv(
        "APP_ENV",
        "development",
    )

    assert isinstance(
        ShopifyProviderFactory.create(),
        FakeShopifyProvider,
    )


def test_production_defaults_real(
    monkeypatch,
):
    clear(monkeypatch)
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )

    assert isinstance(
        ShopifyProviderFactory.create(),
        RealShopifyProvider,
    )


def test_explicit_true_real(
    monkeypatch,
):
    clear(monkeypatch)
    monkeypatch.setenv(
        "APP_ENV",
        "development",
    )
    monkeypatch.setenv(
        "SHOPIFY_USE_REAL_PROVIDER",
        "true",
    )

    assert isinstance(
        ShopifyProviderFactory.create(),
        RealShopifyProvider,
    )


def test_explicit_false_fake(
    monkeypatch,
):
    clear(monkeypatch)
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "SHOPIFY_USE_REAL_PROVIDER",
        "false",
    )

    assert isinstance(
        ShopifyProviderFactory.create(),
        FakeShopifyProvider,
    )
