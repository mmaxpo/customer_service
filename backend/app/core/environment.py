from __future__ import annotations

import os


_DEVELOPMENT_ENVIRONMENTS = {
    "",
    "dev",
    "development",
    "local",
}

_TEST_ENVIRONMENTS = {
    "test",
    "testing",
}

_STAGING_ENVIRONMENTS = {
    "stage",
    "staging",
}

_PRODUCTION_ENVIRONMENTS = {
    "prod",
    "production",
}


def application_environment() -> str:
    """
    Return the canonical application environment.

    APP_ENV is authoritative when present. ENVIRONMENT remains
    supported for compatibility with existing deployments.
    """

    raw = os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "development"

    return raw.strip().lower()


def is_production_environment() -> bool:
    return application_environment() in _PRODUCTION_ENVIRONMENTS


def validate_environment_name() -> str:
    """
    Validate and return the normalized application environment.

    Unknown values are rejected instead of silently falling back
    to development behavior.
    """

    environment = application_environment()

    allowed = (
        _DEVELOPMENT_ENVIRONMENTS
        | _TEST_ENVIRONMENTS
        | _STAGING_ENVIRONMENTS
        | _PRODUCTION_ENVIRONMENTS
    )

    if environment not in allowed:
        raise RuntimeError(f"Unsupported application environment: {environment!r}")

    return environment


__all__ = [
    "application_environment",
    "is_production_environment",
    "validate_environment_name",
]
