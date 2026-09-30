from __future__ import annotations

import os

from app.core.config import settings
from app.core.environment import (
    is_production_environment,
)
from app.domains.customer_service.integrations.shopify.real_provider import (
    RealShopifyProvider,
)
from app.domains.customer_service.providers.shopify import (
    FakeShopifyProvider,
)


class ShopifyProviderFactory:
    @staticmethod
    def create(
        *,
        use_real_provider: bool = False,
    ):
        if os.getenv("PYTEST_CURRENT_TEST"):
            return FakeShopifyProvider()

        raw_env = os.getenv("SHOPIFY_USE_REAL_PROVIDER")

        if raw_env is not None:
            normalized = raw_env.strip().lower()

            if normalized in {
                "0",
                "false",
                "no",
                "off",
            }:
                return FakeShopifyProvider()

            if normalized in {
                "1",
                "true",
                "yes",
                "on",
            }:
                return RealShopifyProvider()

        if use_real_provider or settings.SHOPIFY_USE_REAL_PROVIDER:
            return RealShopifyProvider()

        if is_production_environment():
            return RealShopifyProvider()

        return FakeShopifyProvider()
