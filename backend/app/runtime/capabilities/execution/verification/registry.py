from __future__ import annotations

from app.runtime.capabilities.execution.verification.contracts import (
    TaskVerificationContext,
    TaskVerificationRequest,
    TaskVerificationResult,
    TaskVerifier,
)


class TaskVerifierRegistry:
    """
    Registry for deterministic business-outcome verifiers.

    Keys describe the provider execution boundary plus the requested action,
    for example:

        shopify.order_action:cancel
        shopify.order_action:refund

    This avoids assuming every business action has a separate provider_ref.
    """

    def __init__(self) -> None:
        self._verifiers: dict[
            str,
            TaskVerifier,
        ] = {}

    def register(
        self,
        key: str,
        verifier: TaskVerifier,
    ) -> None:
        normalized = self._normalize_key(
            key
        )

        if normalized in self._verifiers:
            raise ValueError(
                "Task verifier already registered: "
                f"{normalized}"
            )

        self._verifiers[normalized] = verifier

    def has(
        self,
        key: str,
    ) -> bool:
        return (
            self._normalize_key(key)
            in self._verifiers
        )

    def get(
        self,
        key: str,
    ) -> TaskVerifier:
        normalized = self._normalize_key(
            key
        )
        verifier = self._verifiers.get(
            normalized
        )

        if verifier is None:
            raise ValueError(
                "No task verifier registered for "
                f"{normalized}"
            )

        return verifier

    def resolve_key(
        self,
        request: TaskVerificationRequest,
    ) -> str:
        provider_ref = str(
            request.provider_ref or ""
        ).strip()
        action = str(
            request.action
            or request.inputs.get("action")
            or ""
        ).strip().lower()

        if not provider_ref:
            raise ValueError(
                "provider_ref is required for "
                "task verification"
            )

        if not action:
            raise ValueError(
                "action is required for task "
                "verification"
            )

        return self._normalize_key(
            f"{provider_ref}:{action}"
        )

    async def verify(
        self,
        context: TaskVerificationContext,
    ) -> TaskVerificationResult:
        key = self.resolve_key(
            context.request
        )
        verifier = self.get(key)
        return await verifier.verify(
            context
        )

    def keys(self) -> tuple[str, ...]:
        return tuple(
            sorted(self._verifiers)
        )

    @staticmethod
    def _normalize_key(
        key: str,
    ) -> str:
        normalized = str(
            key or ""
        ).strip().lower()

        if not normalized:
            raise ValueError(
                "task verifier key is required"
            )

        return normalized


__all__ = [
    "TaskVerifierRegistry",
]
