from app.runtime.capabilities.execution.verification.providers.shopify import (
    register_shopify_task_verifiers,
)
from app.runtime.capabilities.execution.verification.registry import (
    TaskVerifierRegistry,
)


def build_default_task_verifier_registry(
) -> TaskVerifierRegistry:
    registry = TaskVerifierRegistry()

    register_shopify_task_verifiers(
        registry
    )

    return registry


__all__ = [
    "build_default_task_verifier_registry",
]
