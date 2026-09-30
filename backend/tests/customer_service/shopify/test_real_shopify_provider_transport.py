from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.domains.customer_service.integrations.shopify.real_provider import (
    RealShopifyProvider,
)
from app.integrations.errors import (
    IntegrationProviderError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)


class FakeAsyncClient:
    def __init__(
        self,
        *,
        request_impl: Callable[..., Any],
        **_: Any,
    ) -> None:
        self.request_impl = request_impl
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        return False

    async def request(
        self,
        method,
        url,
        **kwargs,
    ):
        self.calls.append(
            {
                "method": method,
                "url": url,
                **kwargs,
            }
        )

        result = self.request_impl(
            method,
            url,
            **kwargs,
        )

        if hasattr(result, "__await__"):
            return await result

        return result


def response(
    status_code: int,
    *,
    json_data: dict | list | None = None,
    text: str | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    request = httpx.Request(
        "GET",
        "https://example.myshopify.com",
    )

    if json_data is not None:
        return httpx.Response(
            status_code,
            json=json_data,
            headers=headers,
            request=request,
        )

    return httpx.Response(
        status_code,
        text=text or "",
        headers=headers,
        request=request,
    )


def install_client(
    monkeypatch,
    request_impl,
):
    created = []

    def factory(**kwargs):
        client = FakeAsyncClient(
            request_impl=request_impl,
            **kwargs,
        )
        created.append(client)
        return client

    monkeypatch.setattr(
        "app.domains.customer_service.integrations."
        "shopify.real_provider.httpx.AsyncClient",
        factory,
    )

    return created


def provider() -> RealShopifyProvider:
    return RealShopifyProvider(
        api_version="2025-01",
        timeout_seconds=20,
    )


@pytest.mark.asyncio
async def test_successful_json_response(
    monkeypatch,
):
    clients = install_client(
        monkeypatch,
        lambda *_args, **_kwargs: response(
            200,
            json_data={
                "shop": {
                    "id": 1,
                }
            },
        ),
    )

    result = await provider()._request(
        "GET",
        shop_domain="example.myshopify.com",
        access_token="secret-token",
        path="/shop.json",
    )

    assert result == {
        "shop": {
            "id": 1,
        }
    }

    assert len(clients) == 1
    assert len(clients[0].calls) == 1

    assert clients[0].calls[0]["headers"]["X-Shopify-Access-Token"] == "secret-token"


@pytest.mark.asyncio
async def test_httpx_timeout_is_normalized(
    monkeypatch,
):
    def fail(*_args, **_kwargs):
        request = httpx.Request(
            "GET",
            "https://example.myshopify.com",
        )

        raise httpx.ReadTimeout(
            "timed out with secret-token",
            request=request,
        )

    install_client(
        monkeypatch,
        fail,
    )

    with pytest.raises(
        IntegrationTimeoutError,
        match=("Shopify Admin API request timed out"),
    ) as caught:
        await provider()._request(
            "GET",
            shop_domain=("example.myshopify.com"),
            access_token="secret-token",
            path="/shop.json",
        )

    assert "secret-token" not in str(caught.value)


@pytest.mark.asyncio
async def test_httpx_network_error_is_normalized(
    monkeypatch,
):
    def fail(*_args, **_kwargs):
        request = httpx.Request(
            "GET",
            "https://example.myshopify.com",
        )

        raise httpx.ConnectError(
            "connection failed with secret-token",
            request=request,
        )

    install_client(
        monkeypatch,
        fail,
    )

    with pytest.raises(
        IntegrationUnavailableError,
        match="transport is unavailable",
    ) as caught:
        await provider()._request(
            "GET",
            shop_domain=("example.myshopify.com"),
            access_token="secret-token",
            path="/shop.json",
        )

    assert "secret-token" not in str(caught.value)


@pytest.mark.asyncio
async def test_429_is_transient_and_parses_retry_after(
    monkeypatch,
):
    install_client(
        monkeypatch,
        lambda *_args, **_kwargs: response(
            429,
            text=("provider raw secret body"),
            headers={
                "Retry-After": "2.5",
            },
        ),
    )

    with pytest.raises(
        IntegrationUnavailableError,
        match="rate limit exceeded",
    ) as caught:
        await provider()._request(
            "GET",
            shop_domain=("example.myshopify.com"),
            access_token="secret-token",
            path="/orders.json",
        )

    assert caught.value.retry_after_seconds == 2.5

    assert "provider raw secret body" not in str(caught.value)

    assert "secret-token" not in str(caught.value)


@pytest.mark.asyncio
async def test_retry_after_is_bounded(
    monkeypatch,
):
    install_client(
        monkeypatch,
        lambda *_args, **_kwargs: response(
            429,
            headers={
                "Retry-After": "9999",
            },
        ),
    )

    with pytest.raises(
        IntegrationUnavailableError,
    ) as caught:
        await provider()._request(
            "GET",
            shop_domain=("example.myshopify.com"),
            access_token="secret-token",
            path="/orders.json",
        )

    assert caught.value.retry_after_seconds == 30.0


@pytest.mark.asyncio
async def test_real_refund_calculates_then_executes_exact_scope(monkeypatch):
    captured = {}
    instance = provider()
    async def fake_graphql(**kwargs):
        captured.update(kwargs)
        return {
            "data": {
                "refundCreate": {
                    "refund": {"id": "gid://shopify/Refund/88"},
                    "userErrors": [],
                }
            }
        }

    monkeypatch.setattr(instance, "_graphql_request", fake_graphql)
    result = await instance.refund_order(
        shop_domain="example.myshopify.com",
        access_token="secret-token",
        order={
            "id": 10,
            "name": "#10",
            "currency": "USD",
            "line_items": [{"id": 101, "quantity": 2}],
            "transactions": [{"id": 7, "gateway": "shopify_payments"}],
        },
        reason="damaged",
        amount="20.00",
        scope={
            "currency": "USD",
            "line_items": [
                {
                    "line_item_id": "101",
                    "quantity": 1,
                    "restock_type": "return",
                }
            ],
        },
    )

    assert result["status"] == "refunded"
    assert result["refund_id"] == "gid://shopify/Refund/88"
    created = captured["variables"]["input"]
    assert created["transactions"][0]["amount"] == "20.00"
    assert created["refundLineItems"][0]["restockType"] == "RETURN"


@pytest.mark.asyncio
async def test_real_reship_creates_replacement_draft(monkeypatch):
    instance = provider()
    captured = {}

    async def fake_graphql(**kwargs):
        captured.update(kwargs)
        return {
            "data": {
                "draftOrderCreate": {
                    "draftOrder": {
                        "id": "gid://shopify/DraftOrder/1",
                        "name": "#D1",
                        "status": "OPEN",
                    },
                    "userErrors": [],
                }
            }
        }

    monkeypatch.setattr(instance, "_graphql_request", fake_graphql)
    result = await instance.reship_order(
        shop_domain="example.myshopify.com",
        access_token="secret-token",
        order={
            "id": 10,
            "name": "#10",
            "line_items": [{"id": 101, "quantity": 2, "variant_id": 501}],
        },
        reason="lost",
        note=None,
        scope={"replacement_line_item_id": "101", "replacement_quantity": 1},
    )

    assert result["status"] == "draft_created"
    assert result["replacement_strategy"] == "draft_order"
    line_item = captured["variables"]["input"]["lineItems"][0]
    assert line_item == {
        "variantId": "gid://shopify/ProductVariant/501",
        "quantity": 1,
    }


@pytest.mark.asyncio
async def test_shopify_billing_checkout_uses_recurring_graphql_plan(monkeypatch):
    instance = provider()
    captured = {}

    async def fake_graphql(**kwargs):
        captured.update(kwargs)
        return {
            "data": {
                "appSubscriptionCreate": {
                    "appSubscription": {
                        "id": "gid://shopify/AppSubscription/42",
                        "name": "Tajeran Growth",
                        "status": "PENDING",
                    },
                    "confirmationUrl": "https://shop.myshopify.com/confirm/42",
                    "userErrors": [],
                }
            }
        }

    monkeypatch.setattr(instance, "_graphql_request", fake_graphql)
    created = await instance.create_app_subscription(
        shop_domain="shop.myshopify.com",
        access_token="token",
        name="Tajeran Growth",
        amount="149.00",
        currency="USD",
        interval="EVERY_30_DAYS",
        return_url="https://app.example.com/settings/billing",
        trial_days=14,
        test=True,
    )

    pricing = captured["variables"]["lineItems"][0]["plan"][
        "appRecurringPricingDetails"
    ]
    assert pricing["price"] == {"amount": "149.00", "currencyCode": "USD"}
    assert pricing["interval"] == "EVERY_30_DAYS"
    assert created["id"] == "gid://shopify/AppSubscription/42"


@pytest.mark.asyncio
async def test_invalid_retry_after_is_ignored(
    monkeypatch,
):
    install_client(
        monkeypatch,
        lambda *_args, **_kwargs: response(
            429,
            headers={
                "Retry-After": ("not-a-number"),
            },
        ),
    )

    with pytest.raises(
        IntegrationUnavailableError,
    ) as caught:
        await provider()._request(
            "GET",
            shop_domain=("example.myshopify.com"),
            access_token="secret-token",
            path="/orders.json",
        )

    assert caught.value.retry_after_seconds is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code",
    [
        500,
        502,
        503,
        504,
    ],
)
async def test_5xx_is_transient_unavailable(
    monkeypatch,
    status_code,
):
    install_client(
        monkeypatch,
        lambda *_args, **_kwargs: response(
            status_code,
            text="raw provider body",
        ),
    )

    with pytest.raises(
        IntegrationUnavailableError,
    ) as caught:
        await provider()._request(
            "GET",
            shop_domain=("example.myshopify.com"),
            access_token="secret-token",
            path="/orders.json",
        )

    assert f"status={status_code}" in str(caught.value)

    assert "raw provider body" not in str(caught.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code",
    [
        400,
        401,
        403,
        404,
        422,
    ],
)
async def test_deterministic_4xx_is_provider_error(
    monkeypatch,
    status_code,
):
    install_client(
        monkeypatch,
        lambda *_args, **_kwargs: response(
            status_code,
            text=("raw body including secret-token"),
        ),
    )

    with pytest.raises(
        IntegrationProviderError,
    ) as caught:
        await provider()._request(
            "GET",
            shop_domain=("example.myshopify.com"),
            access_token="secret-token",
            path="/orders.json",
        )

    message = str(caught.value)

    assert f"status={status_code}" in message

    assert "raw body" not in message
    assert "secret-token" not in message


@pytest.mark.asyncio
async def test_401_message_preserves_router_detection(
    monkeypatch,
):
    install_client(
        monkeypatch,
        lambda *_args, **_kwargs: response(
            401,
        ),
    )

    with pytest.raises(
        IntegrationProviderError,
    ) as caught:
        await provider()._request(
            "GET",
            shop_domain=("example.myshopify.com"),
            access_token="secret-token",
            path="/orders.json",
        )

    # Existing HTTP adapter recognizes the stable
    # provider status marker.
    assert "401" in str(caught.value)


@pytest.mark.asyncio
async def test_empty_success_returns_empty_dict(
    monkeypatch,
):
    install_client(
        monkeypatch,
        lambda *_args, **_kwargs: response(
            204,
        ),
    )

    result = await provider()._request(
        "DELETE",
        shop_domain="example.myshopify.com",
        access_token="secret-token",
        path="/resource.json",
    )

    assert result == {}


@pytest.mark.asyncio
async def test_invalid_success_json_is_provider_error(
    monkeypatch,
):
    install_client(
        monkeypatch,
        lambda *_args, **_kwargs: response(
            200,
            text="<html>not json</html>",
        ),
    )

    with pytest.raises(
        IntegrationProviderError,
        match="returned invalid JSON",
    ):
        await provider()._request(
            "GET",
            shop_domain=("example.myshopify.com"),
            access_token="secret-token",
            path="/orders.json",
        )


@pytest.mark.asyncio
async def test_unexpected_json_shape_is_provider_error(
    monkeypatch,
):
    install_client(
        monkeypatch,
        lambda *_args, **_kwargs: response(
            200,
            json_data=[
                {
                    "id": 1,
                }
            ],
        ),
    )

    with pytest.raises(
        IntegrationProviderError,
        match="unexpected payload",
    ):
        await provider()._request(
            "GET",
            shop_domain=("example.myshopify.com"),
            access_token="secret-token",
            path="/orders.json",
        )
