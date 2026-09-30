"""
Runtime resources.

- models.py: resources available to runtime
- build.py: builds the resources
- access.py: gets or repairs resources for a running context

Construction and access are loaded lazily so importing resource models does
not bootstrap the capability system.
"""

from app.runtime.resources.models import (
    AIServices,
    BusinessServices,
    DataServices,
    IdentityServices,
    InfrastructureServices,
    RuntimeKernelServices,
    RuntimeServices,
)


def __getattr__(name: str):
    """Load runtime construction helpers only when requested."""

    if name == "RuntimeServiceFactory":
        from app.runtime.resources.build import RuntimeServiceFactory

        return RuntimeServiceFactory

    if name == "get_runtime_services":
        from app.runtime.resources.access import get_runtime_services

        return get_runtime_services

    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )


__all__ = [
    "AIServices",
    "BusinessServices",
    "DataServices",
    "IdentityServices",
    "InfrastructureServices",
    "RuntimeKernelServices",
    "RuntimeServiceFactory",
    "RuntimeServices",
    "get_runtime_services",
]
