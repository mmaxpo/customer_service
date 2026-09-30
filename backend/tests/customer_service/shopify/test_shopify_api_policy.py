from app.core.config import settings
from app.domains.customer_service.integrations.shopify.real_provider import (
    RealShopifyProvider,
)


def test_shopify_v1_is_pinned_to_the_current_stable_graphql_version():
    assert settings.SHOPIFY_API_VERSION == "2026-07"


def test_real_shopify_provider_uses_graphql_for_admin_requests():
    provider = RealShopifyProvider(api_version="2026-07")
    assert provider.api_version == "2026-07"
    # The provider's sole live request path is assembled by _graphql_request.
    # Keep the REST-style transport helper private to avoid new REST callers.
    assert "/graphql.json" in RealShopifyProvider._graphql_request.__code__.co_consts
