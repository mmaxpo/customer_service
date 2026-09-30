from __future__ import annotations

import os
import re
from urllib.parse import urlsplit

from cryptography.fernet import Fernet

from app.core.cors import cors_allowed_origins
from app.core.environment import (
    is_production_environment,
    validate_environment_name,
)


_ALLOWED_SAMESITE = {
    "lax",
    "strict",
    "none",
}

_LOCAL_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
}

# Shopify 2026-07 is the current stable Admin API release selected for V1.
# Pinning avoids Shopify's automatic fall-forward behavior at version expiry.
_SUPPORTED_SHOPIFY_API_VERSIONS = {"2026-07"}


def _required_environment_secret(
    *names: str,
) -> str:
    for name in names:
        value = os.getenv(name)

        if value and value.strip():
            return value.strip()

    joined = " or ".join(names)

    raise RuntimeError(f"{joined} is required in production")


def _validate_fernet_key(
    value: str,
    *,
    label: str,
) -> None:
    try:
        Fernet(value.encode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"{label} must be a valid Fernet key") from exc


def _validate_secret_key(
    value: str,
) -> None:
    secret = value.strip()

    if len(secret) < 32:
        raise RuntimeError(
            "SECRET_KEY must contain at least 32 characters in production"
        )

    weak_values = {
        "secret",
        "changeme",
        "change-me",
        "development",
        "development-secret",
        "dev-secret",
        "test",
        "testing",
    }

    if secret.lower() in weak_values:
        raise RuntimeError("SECRET_KEY uses an unsafe production value")


def _validate_shopify_redirect_uri(
    value: str,
) -> None:
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise RuntimeError("SHOPIFY_REDIRECT_URI is invalid") from exc

    if parsed.scheme.lower() != "https":
        raise RuntimeError("SHOPIFY_REDIRECT_URI must use HTTPS in production")

    hostname = (parsed.hostname or "").strip().lower()

    if not hostname or hostname in _LOCAL_HOSTNAMES:
        raise RuntimeError(
            "SHOPIFY_REDIRECT_URI must use a non-local production hostname"
        )


def _validate_shopify_api_version(value: str) -> None:
    version = str(value or "").strip()
    if not re.fullmatch(r"20\d{2}-(01|04|07|10)", version):
        raise RuntimeError("SHOPIFY_API_VERSION must use Shopify's YYYY-MM format")
    if version not in _SUPPORTED_SHOPIFY_API_VERSIONS:
        raise RuntimeError(
            "SHOPIFY_API_VERSION must be a currently supported V1 version; "
            f"expected one of {sorted(_SUPPORTED_SHOPIFY_API_VERSIONS)}"
        )


def validate_startup_configuration(
    settings,
) -> None:
    """
    Fail application startup when environment/security settings
    are incompatible with production operation.

    Development and test environments retain their current
    permissive behavior.
    """

    validate_environment_name()
    cors_allowed_origins()

    samesite = str(settings.COOKIE_SAMESITE).strip().lower()

    if samesite not in _ALLOWED_SAMESITE:
        raise RuntimeError("COOKIE_SAMESITE must be one of: lax, strict, none")

    if not is_production_environment():
        return

    if settings.COOKIE_SECURE is not True:
        raise RuntimeError("COOKIE_SECURE must be true in production")

    if settings.CSRF_ENFORCED is not True:
        raise RuntimeError("CSRF_ENFORCED must be true in production")

    if not settings.REDIS_URL:
        raise RuntimeError("REDIS_URL is required in production")

    billing_secret = str(getattr(settings, "BILLING_WEBHOOK_SECRET", "") or "")
    if len(billing_secret) < 32:
        raise RuntimeError(
            "BILLING_WEBHOOK_SECRET must contain at least 32 characters in production"
        )
    if getattr(settings, "SHOPIFY_BILLING_TEST", True):
        raise RuntimeError("SHOPIFY_BILLING_TEST must be false in production")

    inbound_email_secret = str(
        getattr(settings, "INBOUND_EMAIL_WEBHOOK_SECRET", "") or ""
    )
    if not inbound_email_secret.startswith("whsec_"):
        raise RuntimeError(
            "INBOUND_EMAIL_WEBHOOK_SECRET must be a Resend/Svix whsec_ secret in production"
        )

    if getattr(settings, "ATTACHMENT_STORAGE_BACKEND", "local") != "s3":
        raise RuntimeError("ATTACHMENT_STORAGE_BACKEND must be s3 in production")
    if not getattr(settings, "S3_BUCKET", None):
        raise RuntimeError("S3_BUCKET is required in production")
    if getattr(settings, "MAX_REQUEST_BODY_BYTES", 0) < getattr(
        settings, "MAX_ATTACHMENT_BYTES", 0
    ):
        raise RuntimeError(
            "MAX_REQUEST_BODY_BYTES must be at least MAX_ATTACHMENT_BYTES"
        )
    if getattr(settings, "ATTACHMENT_SCAN_MODE", "") != "clamdscan":
        raise RuntimeError("ATTACHMENT_SCAN_MODE must be clamdscan in production")

    _validate_secret_key(settings.SECRET_KEY)

    _validate_shopify_redirect_uri(settings.SHOPIFY_REDIRECT_URI)
    _validate_shopify_api_version(settings.SHOPIFY_API_VERSION)

    shopify_encryption_key = _required_environment_secret(
        "SHOPIFY_TOKEN_ENCRYPTION_KEY",
        "TAJERAN_ENCRYPTION_KEY",
    )

    _validate_fernet_key(
        shopify_encryption_key,
        label=("SHOPIFY_TOKEN_ENCRYPTION_KEY/TAJERAN_ENCRYPTION_KEY"),
    )

    field_encryption_key = _required_environment_secret(
        "TAJERAN_FIELD_ENCRYPTION_KEY",
        "SHOPIFY_TOKEN_ENCRYPTION_KEY",
    )

    _validate_fernet_key(
        field_encryption_key,
        label=("TAJERAN_FIELD_ENCRYPTION_KEY/SHOPIFY_TOKEN_ENCRYPTION_KEY"),
    )


__all__ = [
    "validate_startup_configuration",
]
