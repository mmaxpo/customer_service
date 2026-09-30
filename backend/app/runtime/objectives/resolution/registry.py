from __future__ import annotations

from app.runtime.objectives.resolution.contracts import (
    ObjectiveResolutionAdapter,
    ObjectiveResolutionAssessment,
    ObjectiveResolutionContext,
)


class ObjectiveResolutionAdapterRegistry:
    """
    Registry of product-owned objective-resolution
    adapters.

    Core resolves by normalized objective namespace and
    objective type. It never imports product modules.
    """

    def __init__(self) -> None:
        self._adapters: dict[
            tuple[str, str],
            ObjectiveResolutionAdapter,
        ] = {}

    def register(
        self,
        *,
        namespace: str,
        objective_type: str,
        adapter: ObjectiveResolutionAdapter,
    ) -> None:
        key = self._normalize_key(
            namespace=namespace,
            objective_type=objective_type,
        )

        if key in self._adapters:
            raise ValueError(
                "Objective resolution adapter already "
                "registered: "
                f"{key[0]}:{key[1]}"
            )

        self._adapters[key] = adapter

    def has(
        self,
        *,
        namespace: str,
        objective_type: str,
    ) -> bool:
        return (
            self._normalize_key(
                namespace=namespace,
                objective_type=objective_type,
            )
            in self._adapters
        )

    def get(
        self,
        *,
        namespace: str,
        objective_type: str,
    ) -> ObjectiveResolutionAdapter:
        key = self._normalize_key(
            namespace=namespace,
            objective_type=objective_type,
        )

        adapter = self._adapters.get(key)

        if adapter is None:
            raise ValueError(
                "No objective resolution adapter "
                "registered for "
                f"{key[0]}:{key[1]}"
            )

        return adapter

    def assess(
        self,
        *,
        namespace: str,
        objective_type: str,
        context: ObjectiveResolutionContext,
    ) -> ObjectiveResolutionAssessment:
        return self.get(
            namespace=namespace,
            objective_type=objective_type,
        ).assess(context)

    def keys(
        self,
    ) -> tuple[tuple[str, str], ...]:
        return tuple(
            sorted(self._adapters)
        )

    @staticmethod
    def _normalize_key(
        *,
        namespace: str,
        objective_type: str,
    ) -> tuple[str, str]:
        normalized_namespace = str(
            namespace or ""
        ).strip().lower()
        normalized_type = str(
            objective_type or ""
        ).strip().lower()

        if not normalized_namespace:
            raise ValueError(
                "objective resolution namespace "
                "is required"
            )

        if not normalized_type:
            raise ValueError(
                "objective resolution objective_type "
                "is required"
            )

        return (
            normalized_namespace,
            normalized_type,
        )


__all__ = [
    "ObjectiveResolutionAdapterRegistry",
]
