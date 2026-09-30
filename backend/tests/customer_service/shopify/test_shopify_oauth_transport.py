import httpx
import pytest

from app.domains.customer_service.integrations.shopify.oauth import (
    ShopifyOAuthService,
)
from app.integrations.errors import (
    IntegrationProviderError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)


class FakeClient:
    def __init__(self, result, **_):
        self.result = result

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        return False

    async def post(
        self,
        *_args,
        **_kwargs,
    ):
        if isinstance(
            self.result,
            Exception,
        ):
            raise self.result

        return self.result


def service():
    return ShopifyOAuthService(
        api_key="key",
        api_secret="secret",
        redirect_uri=(
            "https://api.example.com/customer-service/shopify/oauth/callback"
        ),
        scopes=["read_orders"],
    )


def install(
    monkeypatch,
    result,
):
    monkeypatch.setattr(
        "app.domains.customer_service.integrations.shopify.oauth.httpx.AsyncClient",
        lambda **kwargs: FakeClient(
            result,
            **kwargs,
        ),
    )


def response(
    status,
    *,
    payload=None,
    text="",
):
    request = httpx.Request(
        "POST",
        "https://example.myshopify.com/admin/oauth/access_token",
    )

    if payload is not None:
        return httpx.Response(
            status,
            json=payload,
            request=request,
        )

    return httpx.Response(
        status,
        text=text,
        request=request,
    )


@pytest.mark.asyncio
async def test_success(
    monkeypatch,
):
    install(
        monkeypatch,
        response(
            200,
            payload={"access_token": "token"},
        ),
    )

    result = await service().exchange_code_for_access_token(
        shop_domain=("example.myshopify.com"),
        code="code",
    )

    assert result["access_token"] == "token"


@pytest.mark.asyncio
async def test_timeout(
    monkeypatch,
):
    request = httpx.Request(
        "POST",
        "https://example.myshopify.com",
    )

    install(
        monkeypatch,
        httpx.ReadTimeout(
            "private detail",
            request=request,
        ),
    )

    with pytest.raises(
        IntegrationTimeoutError,
    ):
        await service().exchange_code_for_access_token(
            shop_domain="example.myshopify.com",
            code="code",
        )


@pytest.mark.asyncio
async def test_network_error(
    monkeypatch,
):
    request = httpx.Request(
        "POST",
        "https://example.myshopify.com",
    )

    install(
        monkeypatch,
        httpx.ConnectError(
            "private detail",
            request=request,
        ),
    )

    with pytest.raises(
        IntegrationUnavailableError,
    ):
        await service().exchange_code_for_access_token(
            shop_domain="example.myshopify.com",
            code="code",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [429, 500, 502, 503, 504],
)
async def test_transient_status(
    monkeypatch,
    status,
):
    install(
        monkeypatch,
        response(
            status,
            text="private provider body",
        ),
    )

    with pytest.raises(
        IntegrationUnavailableError,
    ) as caught:
        await service().exchange_code_for_access_token(
            shop_domain="example.myshopify.com",
            code="code",
        )

    assert "private provider body" not in str(caught.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [400, 401, 403, 404, 422],
)
async def test_4xx(
    monkeypatch,
    status,
):
    install(
        monkeypatch,
        response(
            status,
            text="private provider body",
        ),
    )

    with pytest.raises(
        IntegrationProviderError,
    ) as caught:
        await service().exchange_code_for_access_token(
            shop_domain="example.myshopify.com",
            code="code",
        )

    assert f"status={status}" in str(caught.value)

    assert "private provider body" not in str(caught.value)


@pytest.mark.asyncio
async def test_invalid_json(
    monkeypatch,
):
    install(
        monkeypatch,
        response(
            200,
            text="<html>bad</html>",
        ),
    )

    with pytest.raises(
        IntegrationProviderError,
    ):
        await service().exchange_code_for_access_token(
            shop_domain="example.myshopify.com",
            code="code",
        )
