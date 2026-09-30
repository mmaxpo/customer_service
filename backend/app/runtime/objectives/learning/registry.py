from __future__ import annotations

from app.runtime.objectives.learning.contracts import (
    ObjectiveLearningProfile,
)


class ObjectiveLearningProfileRegistry:
    """
    In-memory versioned profile registry.

    Registration is explicit and product-owned. The generic runtime
    does not import product domains or create default product
    profiles.
    """

    def __init__(self) -> None:
        self._profiles: dict[
            tuple[str, str, int],
            ObjectiveLearningProfile,
        ] = {}

    def register(
        self,
        profile: ObjectiveLearningProfile,
    ) -> None:
        key = self._version_key(
            namespace=profile.objective_namespace,
            objective_type=profile.objective_type,
            profile_version=profile.profile_version,
        )

        if key in self._profiles:
            raise ValueError(
                "Objective learning profile version already "
                "registered: "
                f"{key[0]}:{key[1]}:v{key[2]}"
            )

        for existing in self._profiles.values():
            if (
                existing.profile_ref == profile.profile_ref
                and existing.profile_version == profile.profile_version
                and (
                    existing.objective_namespace != profile.objective_namespace
                    or existing.objective_type != profile.objective_type
                )
            ):
                raise ValueError(
                    "Objective learning profile identity "
                    "already registered for another "
                    "objective family"
                )

        self._profiles[key] = profile

    def has(
        self,
        *,
        namespace: str,
        objective_type: str,
        profile_version: int | None = None,
    ) -> bool:
        if profile_version is not None:
            return (
                self._version_key(
                    namespace=namespace,
                    objective_type=objective_type,
                    profile_version=profile_version,
                )
                in self._profiles
            )

        normalized = self._family_key(
            namespace=namespace,
            objective_type=objective_type,
        )

        return any(key[:2] == normalized for key in self._profiles)

    def get(
        self,
        *,
        namespace: str,
        objective_type: str,
        profile_version: int | None = None,
    ) -> ObjectiveLearningProfile:
        family = self._family_key(
            namespace=namespace,
            objective_type=objective_type,
        )

        if profile_version is not None:
            profile = self._profiles.get(
                (
                    family[0],
                    family[1],
                    self._normalize_version(profile_version),
                )
            )

            if profile is None:
                raise ValueError(
                    "No objective learning profile "
                    "registered for "
                    f"{family[0]}:{family[1]}:"
                    f"v{profile_version}"
                )

            return profile

        matches = [
            profile for key, profile in self._profiles.items() if key[:2] == family
        ]

        if not matches:
            raise ValueError(
                f"No objective learning profile registered for {family[0]}:{family[1]}"
            )

        return max(
            matches,
            key=lambda item: item.profile_version,
        )

    def versions(
        self,
        *,
        namespace: str,
        objective_type: str,
    ) -> tuple[int, ...]:
        family = self._family_key(
            namespace=namespace,
            objective_type=objective_type,
        )

        return tuple(sorted(key[2] for key in self._profiles if key[:2] == family))

    def keys(
        self,
    ) -> tuple[tuple[str, str, int], ...]:
        return tuple(sorted(self._profiles))

    @classmethod
    def _version_key(
        cls,
        *,
        namespace: str,
        objective_type: str,
        profile_version: int,
    ) -> tuple[str, str, int]:
        family = cls._family_key(
            namespace=namespace,
            objective_type=objective_type,
        )

        return (
            family[0],
            family[1],
            cls._normalize_version(profile_version),
        )

    @staticmethod
    def _family_key(
        *,
        namespace: str,
        objective_type: str,
    ) -> tuple[str, str]:
        normalized_namespace = str(namespace or "").strip().lower()
        normalized_type = str(objective_type or "").strip().lower()

        if not normalized_namespace:
            raise ValueError("objective learning namespace is required")

        if not normalized_type:
            raise ValueError("objective learning objective_type is required")

        return (
            normalized_namespace,
            normalized_type,
        )

    @staticmethod
    def _normalize_version(
        profile_version: int,
    ) -> int:
        normalized = int(profile_version)

        if normalized < 1:
            raise ValueError("objective learning profile_version must be at least 1")

        return normalized


def build_default_objective_learning_profile_registry() -> (
    ObjectiveLearningProfileRegistry
):
    """
    Build the product-neutral default registry.

    Product composition roots may register profiles explicitly.
    Core defaults never import product domains.
    """

    return ObjectiveLearningProfileRegistry()


__all__ = [
    "ObjectiveLearningProfileRegistry",
    "build_default_objective_learning_profile_registry",
]
