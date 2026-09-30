from __future__ import annotations

from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from app.core.environment import (
    application_environment,
    is_production_environment,
    validate_environment_name,
)
from app.core.startup_validation import (
    validate_startup_configuration,
)


def settings(
    *,
    cookie_secure: bool = True,
    cookie_samesite: str = "lax",
    secret_key: str = "x" * 48,
    csrf_enforced: bool = True,
    redis_url: str | None = "redis://redis:6379/0",
    redirect_uri: str = (
        "https://api.example.com/customer-service/shopify/oauth/callback"
    ),
    shopify_api_version: str = "2026-07",
    billing_webhook_secret: str = "b" * 48,
    inbound_email_webhook_secret: str = "whsec_" + "e" * 48,
    attachment_storage_root: str = "/var/lib/tajeran/attachments",
    attachment_storage_backend: str = "s3",
    attachment_scan_mode: str = "clamdscan",
    s3_bucket: str | None = "tajeran-production-attachments",
):
    return SimpleNamespace(
        COOKIE_SECURE=cookie_secure,
        COOKIE_SAMESITE=cookie_samesite,
        SECRET_KEY=secret_key,
        CSRF_ENFORCED=csrf_enforced,
        REDIS_URL=redis_url,
        SHOPIFY_REDIRECT_URI=redirect_uri,
        SHOPIFY_API_VERSION=shopify_api_version,
        BILLING_WEBHOOK_SECRET=billing_webhook_secret,
        SHOPIFY_BILLING_TEST=False,
        INBOUND_EMAIL_WEBHOOK_SECRET=inbound_email_webhook_secret,
        ATTACHMENT_STORAGE_ROOT=attachment_storage_root,
        MAX_REQUEST_BODY_BYTES=12_000_000,
        MAX_ATTACHMENT_BYTES=10_000_000,
        ATTACHMENT_SCAN_MODE=attachment_scan_mode,
        ATTACHMENT_STORAGE_BACKEND=attachment_storage_backend,
        S3_BUCKET=s3_bucket,
    )


def install_production_environment(
    monkeypatch,
):
    key = Fernet.generate_key().decode("utf-8")

    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://app.example.com",
    )
    monkeypatch.delenv(
        "ENVIRONMENT",
        raising=False,
    )
    monkeypatch.setenv(
        "SHOPIFY_TOKEN_ENCRYPTION_KEY",
        key,
    )
    monkeypatch.setenv(
        "TAJERAN_FIELD_ENCRYPTION_KEY",
        key,
    )

    return key


def test_environment_defaults_to_development(
    monkeypatch,
):
    monkeypatch.delenv(
        "APP_ENV",
        raising=False,
    )
    monkeypatch.delenv(
        "ENVIRONMENT",
        raising=False,
    )

    assert application_environment() == "development"
    assert is_production_environment() is False


def test_app_env_precedes_legacy_environment(
    monkeypatch,
):
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "ENVIRONMENT",
        "development",
    )

    assert application_environment() == "production"
    assert is_production_environment() is True


def test_unknown_environment_is_rejected(
    monkeypatch,
):
    monkeypatch.setenv(
        "APP_ENV",
        "mystery",
    )

    with pytest.raises(
        RuntimeError,
        match="Unsupported application environment",
    ):
        validate_environment_name()


def test_development_keeps_current_permissive_security(
    monkeypatch,
):
    monkeypatch.setenv(
        "APP_ENV",
        "development",
    )

    validate_startup_configuration(
        settings(
            cookie_secure=False,
            secret_key="dev",
            redirect_uri=(
                "http://localhost:8000/customer-service/shopify/oauth/callback"
            ),
        )
    )


def test_invalid_samesite_is_rejected_in_all_environments(
    monkeypatch,
):
    monkeypatch.setenv(
        "APP_ENV",
        "development",
    )

    with pytest.raises(
        RuntimeError,
        match="COOKIE_SAMESITE",
    ):
        validate_startup_configuration(
            settings(
                cookie_samesite="invalid",
            )
        )


def test_production_accepts_secure_configuration(
    monkeypatch,
):
    install_production_environment(monkeypatch)

    validate_startup_configuration(settings())


def test_production_rejects_unapproved_shopify_api_version(
    monkeypatch,
):
    install_production_environment(monkeypatch)

    with pytest.raises(RuntimeError, match="SHOPIFY_API_VERSION"):
        validate_startup_configuration(settings(shopify_api_version="2025-01"))


def test_production_requires_secure_cookie(
    monkeypatch,
):
    install_production_environment(monkeypatch)

    with pytest.raises(
        RuntimeError,
        match="COOKIE_SECURE",
    ):
        validate_startup_configuration(
            settings(
                cookie_secure=False,
            )
        )


def test_production_requires_csrf_and_shared_rate_limit_store(monkeypatch):
    install_production_environment(monkeypatch)

    with pytest.raises(RuntimeError, match="CSRF_ENFORCED"):
        validate_startup_configuration(settings(csrf_enforced=False))

    with pytest.raises(RuntimeError, match="REDIS_URL"):
        validate_startup_configuration(settings(redis_url=None))


def test_production_requires_commercial_webhooks_and_durable_attachments(monkeypatch):
    install_production_environment(monkeypatch)

    with pytest.raises(RuntimeError, match="BILLING_WEBHOOK_SECRET"):
        validate_startup_configuration(settings(billing_webhook_secret="short"))
    with pytest.raises(RuntimeError, match="INBOUND_EMAIL_WEBHOOK_SECRET"):
        validate_startup_configuration(settings(inbound_email_webhook_secret=""))
    with pytest.raises(RuntimeError, match="ATTACHMENT_STORAGE_BACKEND"):
        validate_startup_configuration(settings(attachment_storage_backend="local"))
    with pytest.raises(RuntimeError, match="S3_BUCKET"):
        validate_startup_configuration(settings(s3_bucket=None))
    with pytest.raises(RuntimeError, match="ATTACHMENT_SCAN_MODE"):
        validate_startup_configuration(settings(attachment_scan_mode="builtin"))


@pytest.mark.parametrize(
    "secret",
    [
        "",
        "short",
        "secret",
        "change-me",
    ],
)
def test_production_rejects_weak_secret_key(
    monkeypatch,
    secret,
):
    install_production_environment(monkeypatch)

    with pytest.raises(
        RuntimeError,
        match="SECRET_KEY",
    ):
        validate_startup_configuration(
            settings(
                secret_key=secret,
            )
        )


@pytest.mark.parametrize(
    "redirect_uri",
    [
        ("http://api.example.com/customer-service/shopify/oauth/callback"),
        ("http://localhost:8000/customer-service/shopify/oauth/callback"),
        ("https://localhost/customer-service/shopify/oauth/callback"),
        ("https://127.0.0.1/customer-service/shopify/oauth/callback"),
    ],
)
def test_production_rejects_unsafe_shopify_redirect(
    monkeypatch,
    redirect_uri,
):
    install_production_environment(monkeypatch)

    with pytest.raises(
        RuntimeError,
        match="SHOPIFY_REDIRECT_URI",
    ):
        validate_startup_configuration(
            settings(
                redirect_uri=redirect_uri,
            )
        )


def test_production_requires_shopify_encryption_key(
    monkeypatch,
):
    install_production_environment(monkeypatch)

    monkeypatch.delenv(
        "SHOPIFY_TOKEN_ENCRYPTION_KEY",
    )
    monkeypatch.delenv(
        "TAJERAN_ENCRYPTION_KEY",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="SHOPIFY_TOKEN_ENCRYPTION_KEY",
    ):
        validate_startup_configuration(settings())


def test_production_requires_field_encryption_key(
    monkeypatch,
):
    install_production_environment(monkeypatch)

    monkeypatch.delenv(
        "TAJERAN_FIELD_ENCRYPTION_KEY",
    )
    monkeypatch.delenv(
        "SHOPIFY_TOKEN_ENCRYPTION_KEY",
    )

    # Preserve the separate Shopify encryption fallback
    # while proving the field-encryption requirement.
    monkeypatch.setenv(
        "TAJERAN_ENCRYPTION_KEY",
        Fernet.generate_key().decode("utf-8"),
    )

    with pytest.raises(
        RuntimeError,
        match="TAJERAN_FIELD_ENCRYPTION_KEY",
    ):
        validate_startup_configuration(settings())


def test_production_rejects_invalid_fernet_key(
    monkeypatch,
):
    install_production_environment(monkeypatch)

    monkeypatch.setenv(
        "SHOPIFY_TOKEN_ENCRYPTION_KEY",
        "not-a-fernet-key",
    )

    with pytest.raises(
        RuntimeError,
        match="valid Fernet key",
    ):
        validate_startup_configuration(settings())
