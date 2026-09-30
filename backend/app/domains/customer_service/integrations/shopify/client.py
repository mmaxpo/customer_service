from __future__ import annotations

from typing import Any, Protocol


class ShopifyClient(Protocol):
    async def get_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order_ref: str,
    ) -> dict[str, Any] | None: ...

    async def refund_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict[str, Any],
        reason: str | None,
        amount: str | None,
        scope: dict | None = None,
    ) -> dict[str, Any]: ...

    async def cancel_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict[str, Any],
        reason: str | None,
    ) -> dict[str, Any]: ...

    async def change_order_address(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict[str, Any],
        new_address: dict[str, Any],
        note: str | None,
    ) -> dict[str, Any]: ...

    async def reship_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict[str, Any],
        reason: str | None,
        note: str | None,
        scope: dict | None = None,
    ) -> dict[str, Any]: ...
