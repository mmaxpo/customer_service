from __future__ import annotations

import os
from urllib.parse import urlsplit

from app.core.environment import (
    is_production_environment,
)


_DEV_DEFAULT_ORIGINS = ("http://localhost:3000",)

_LOCAL_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
}


def cors_allowed_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "",
    ).strip()

    if raw:
        origins = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    else:
        origins = list(_DEV_DEFAULT_ORIGINS)

    if not origins:
        raise RuntimeError("CORS_ALLOWED_ORIGINS must contain at least one origin")

    if "*" in origins:
        raise RuntimeError(
            "Wildcard CORS origin is incompatible with credentialed requests"
        )

    if not is_production_environment():
        return origins

    if not raw:
        raise RuntimeError("CORS_ALLOWED_ORIGINS is required in production")

    for origin in origins:
        parsed = urlsplit(origin)

        if parsed.scheme.lower() != "https":
            raise RuntimeError("Production CORS origins must use HTTPS")

        hostname = (parsed.hostname or "").lower()

        if not hostname or hostname in _LOCAL_HOSTNAMES:
            raise RuntimeError("Production CORS origins must use non-local hostnames")

    return origins


__all__ = [
    "cors_allowed_origins",
]
