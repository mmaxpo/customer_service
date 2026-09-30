from __future__ import annotations

from typing import Any, Protocol

from app.domains.customer_service.services.support.commerce.commerce_order import (
    CommerceOrder,
)


class CommerceOrderAdapter(Protocol):
    def adapt(
        self,
        order: dict[str, Any],
    ) -> CommerceOrder: ...


class CommerceOrderAdapterRegistry:
    """
    Product-owned registry that translates provider-specific commerce
    payloads into the provider-neutral CommerceOrder contract.

    Runtime capability resolution chooses the provider. This registry only
    owns provider-result normalization for customer-service product logic.
    """

    def __init__(self) -> None:
        self._by_provider_id: dict[str, CommerceOrderAdapter] = {}
        self._by_provider_ref: dict[str, CommerceOrderAdapter] = {}

    def register(
        self,
        *,
        adapter: CommerceOrderAdapter,
        provider_id: str | None = None,
        provider_ref: str | None = None,
    ) -> None:
        normalized_provider_id = self._optional_key(provider_id)
        normalized_provider_ref = self._optional_key(provider_ref)

        if (
            normalized_provider_id is None
            and normalized_provider_ref is None
        ):
            raise ValueError(
                "Commerce adapter registration requires "
                "provider_id or provider_ref"
            )

        if normalized_provider_id is not None:
            if normalized_provider_id in self._by_provider_id:
                raise ValueError(
                    "Commerce adapter already registered for "
                    f"provider_id={normalized_provider_id!r}"
                )

            self._by_provider_id[normalized_provider_id] = adapter

        if normalized_provider_ref is not None:
            if normalized_provider_ref in self._by_provider_ref:
                raise ValueError(
                    "Commerce adapter already registered for "
                    f"provider_ref={normalized_provider_ref!r}"
                )

            self._by_provider_ref[normalized_provider_ref] = adapter

    def get(
        self,
        *,
        provider_id: str | None,
        provider_ref: str | None,
    ) -> CommerceOrderAdapter:
        normalized_provider_ref = self._optional_key(provider_ref)

        if normalized_provider_ref is not None:
            adapter = self._by_provider_ref.get(
                normalized_provider_ref
            )

            if adapter is not None:
                return adapter

        normalized_provider_id = self._optional_key(provider_id)

        if normalized_provider_id is not None:
            adapter = self._by_provider_id.get(
                normalized_provider_id
            )

            if adapter is not None:
                return adapter

        raise ValueError(
            "No customer-service commerce adapter registered for "
            f"provider_id={provider_id!r}, "
            f"provider_ref={provider_ref!r}"
        )

    def adapt(
        self,
        *,
        provider_id: str | None,
        provider_ref: str | None,
        payload: dict[str, Any],
    ) -> CommerceOrder:
        return self.get(
            provider_id=provider_id,
            provider_ref=provider_ref,
        ).adapt(payload)

    @staticmethod
    def _optional_key(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip().lower()
        return normalized or None


__all__ = [
    "CommerceOrderAdapter",
    "CommerceOrderAdapterRegistry",
]
