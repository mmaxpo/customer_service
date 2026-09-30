from __future__ import annotations

from typing import Any

from app.runtime.capabilities.execution.contracts import (
    CapabilityExecutionContext,
    CapabilityExecutor,
)


class CapabilityExecutorRegistry:
    """
    Runtime registry mapping semantic resolution provider_ref values to
    executable provider callables.

    The semantic capability system owns capability discovery, policy
    evaluation, and provider selection. This registry owns only the final
    execution dispatch boundary.
    """

    def __init__(self) -> None:
        self._executors: dict[str, CapabilityExecutor] = {}

    def register(
        self,
        provider_ref: str,
        executor: CapabilityExecutor,
    ) -> None:
        normalized = self._normalize_provider_ref(provider_ref)

        if normalized in self._executors:
            raise ValueError(
                f"Capability executor already registered: {normalized}"
            )

        self._executors[normalized] = executor

    def has(self, provider_ref: str) -> bool:
        normalized = self._normalize_provider_ref(provider_ref)
        return normalized in self._executors

    def get(self, provider_ref: str) -> CapabilityExecutor:
        normalized = self._normalize_provider_ref(provider_ref)
        executor = self._executors.get(normalized)

        if executor is None:
            raise ValueError(
                "No runtime provider executor registered for "
                f"{normalized}"
            )

        return executor

    async def execute(
        self,
        provider_ref: str,
        context: CapabilityExecutionContext,
    ) -> Any:
        executor = self.get(provider_ref)
        return await executor(context)

    def provider_refs(self) -> tuple[str, ...]:
        return tuple(sorted(self._executors))

    @staticmethod
    def _normalize_provider_ref(provider_ref: str) -> str:
        normalized = str(provider_ref or "").strip()

        if not normalized:
            raise ValueError("provider_ref is required")

        return normalized


__all__ = ["CapabilityExecutorRegistry"]
