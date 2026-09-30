from __future__ import annotations

from dataclasses import dataclass

from app.runtime.capabilities.execution.registry import (
    CapabilityExecutorRegistry,
)
from app.runtime.capabilities.registry.system import (
    CapabilitySystem,
)


@dataclass(frozen=True)
class CapabilityExecutorCoverageReport:
    """
    Consistency report between enabled semantic provider bindings and
    registered runtime executors.
    """

    enabled_provider_refs: tuple[str, ...]
    registered_provider_refs: tuple[str, ...]
    missing_executor_refs: tuple[str, ...]
    unused_executor_refs: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing_executor_refs

    def require_complete(self) -> None:
        if self.ok:
            return

        missing = ", ".join(self.missing_executor_refs)

        raise ValueError(
            "Enabled capability bindings are missing runtime executors: "
            f"{missing}"
        )


def validate_executor_coverage(
    *,
    system: CapabilitySystem,
    executors: CapabilityExecutorRegistry,
) -> CapabilityExecutorCoverageReport:
    """
    Compare enabled provider bindings with the executor registry.

    Disabled bindings are intentionally ignored because they cannot be selected
    by the semantic resolution pipeline.
    """

    enabled_provider_refs = tuple(
        sorted(
            {
                binding.provider_ref.strip()
                for binding in system.bindings.list()
                if binding.enabled and binding.provider_ref.strip()
            }
        )
    )

    registered_provider_refs = executors.provider_refs()

    enabled_set = set(enabled_provider_refs)
    registered_set = set(registered_provider_refs)

    return CapabilityExecutorCoverageReport(
        enabled_provider_refs=enabled_provider_refs,
        registered_provider_refs=registered_provider_refs,
        missing_executor_refs=tuple(
            sorted(enabled_set - registered_set)
        ),
        unused_executor_refs=tuple(
            sorted(registered_set - enabled_set)
        ),
    )


__all__ = [
    "CapabilityExecutorCoverageReport",
    "validate_executor_coverage",
]
