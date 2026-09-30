from __future__ import annotations

from enum import StrEnum


class ProviderHealthEnforcementMode(StrEnum):
    """
    Runtime behavior for durable scoped provider health.

    OFF:
        Do not query durable health.

    SHADOW:
        Query and report health without changing selection.

    ENFORCE_UNHEALTHY:
        Reject only providers whose effective scoped state is unhealthy.
        Missing state and reader failures remain fail-open.
    """

    OFF = "off"
    SHADOW = "shadow"
    ENFORCE_UNHEALTHY = "enforce_unhealthy"


def normalize_provider_health_enforcement_mode(
    value: ProviderHealthEnforcementMode | str | None,
) -> ProviderHealthEnforcementMode:
    if value is None:
        return ProviderHealthEnforcementMode.SHADOW

    if isinstance(
        value,
        ProviderHealthEnforcementMode,
    ):
        return value

    try:
        return ProviderHealthEnforcementMode(
            str(value).strip().lower()
        )
    except ValueError as exc:
        allowed = ", ".join(
            item.value
            for item in ProviderHealthEnforcementMode
        )
        raise ValueError(
            "provider_health_mode must be one of: "
            f"{allowed}"
        ) from exc


__all__ = [
    "ProviderHealthEnforcementMode",
    "normalize_provider_health_enforcement_mode",
]
