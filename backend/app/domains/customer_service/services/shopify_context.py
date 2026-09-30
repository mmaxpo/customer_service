from __future__ import annotations

import re


class ShopifyOrderReferenceExtractor:
    ORDER_PATTERNS = [
        re.compile(r"(?:order|#)\s*#?([A-Za-z0-9-]{3,})", re.IGNORECASE),
        re.compile(r"#([A-Za-z0-9-]{3,})"),
    ]

    def extract(self, text: str) -> str | None:
        value = text or ""

        for pattern in self.ORDER_PATTERNS:
            match = pattern.search(value)
            if match:
                ref = match.group(1).strip()
                return ref if ref.startswith("#") else ref

        return None


class ShopifyOrderContextResolver:
    def __init__(self, db):
        self.db = db
        self.extractor = ShopifyOrderReferenceExtractor()

    async def resolve(self, *, user_id, message: str) -> dict | None:
        from app.domains.customer_service.services.shopify import ShopifyService

        order_ref = self.extractor.extract(message)
        if not order_ref:
            return None

        try:
            order = await ShopifyService(self.db).get_order(
                user_id=user_id,
                order_ref=order_ref,
            )
        except Exception:
            return {
                "order_ref": order_ref,
                "found": False,
            }

        return {
            "order_ref": order_ref,
            "found": True,
            "order": order,
        }
