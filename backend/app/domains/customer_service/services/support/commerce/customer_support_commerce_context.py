from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domains.customer_service.services.support.commerce.commerce_order import (
    CommerceOrder,
)
from app.domains.customer_service.providers.commerce import (
    CommerceOrderAdapterRegistry,
)
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)


@dataclass(frozen=True)
class CustomerSupportCommerceOrderRead:
    found: bool
    order: CommerceOrder | None
    order_ref: str
    provider_id: str | None = None
    provider_ref: str | None = None
    customer_safe_note: str | None = None


class CustomerSupportCommerceContextService:
    """
    Resolve commerce context through semantic runtime capabilities.

    Customer-support orchestration asks for business capability
    `ecommerce.orders.get`; provider resolution and execution remain owned by
    the generic runtime capability system.
    """

    def __init__(
        self,
        *,
        capabilities: Any,
        commerce_adapters: CommerceOrderAdapterRegistry,
    ):
        self.capabilities = capabilities
        self.commerce_adapters = commerce_adapters

    async def get_order(
        self,
        *,
        user_id: Any,
        order_ref: str,
    ) -> CustomerSupportCommerceOrderRead:
        normalized_ref = str(order_ref or "").strip()
        if not normalized_ref:
            raise ValueError("Customer support commerce context requires order_ref")

        result = await self.capabilities.resolve(
            CapabilityInvocation(
                capability_id="ecommerce.orders.get",
                inputs={"order_ref": normalized_ref},
                user_id=user_id,
                metadata={
                    "source": "customer_service.support_orchestration",
                },
            )
        )

        if not result.ok:
            raise RuntimeError(
                result.error_message
                or "Unable to resolve ecommerce.orders.get"
            )

        output = result.output
        if not isinstance(output, dict):
            raise RuntimeError(
                "ecommerce.orders.get returned an invalid result"
            )

        provider_id = self._optional_string(
            result.metadata.get("selected_provider_id")
        )
        provider_ref = self._optional_string(
            result.metadata.get("provider_ref")
        )

        if output.get("found") is False:
            summary = output.get("summary")
            customer_safe_note = (
                summary.get("customer_safe_note")
                if isinstance(summary, dict)
                else None
            )

            return CustomerSupportCommerceOrderRead(
                found=False,
                order=None,
                order_ref=normalized_ref,
                provider_id=provider_id,
                provider_ref=provider_ref,
                customer_safe_note=customer_safe_note,
            )

        payload = output.get("payload")
        if not isinstance(payload, dict):
            raise RuntimeError(
                "ecommerce.orders.get returned no order payload"
            )

        order = self.commerce_adapters.adapt(
            provider_id=provider_id,
            provider_ref=provider_ref,
            payload=payload,
        )

        return CustomerSupportCommerceOrderRead(
            found=True,
            order=order,
            order_ref=normalized_ref,
            provider_id=provider_id,
            provider_ref=provider_ref,
        )

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()
        return normalized or None


__all__ = [
    "CustomerSupportCommerceContextService",
    "CustomerSupportCommerceOrderRead",
]
