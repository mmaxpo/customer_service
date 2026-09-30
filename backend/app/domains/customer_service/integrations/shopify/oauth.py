from __future__ import annotations

import hashlib
import hmac
import re
from urllib.parse import urlencode, urlsplit

import httpx

from app.integrations.errors import (
    IntegrationProviderError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)

SHOP_DOMAIN_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}\.myshopify\.com$")


class ShopifyOAuthService:
    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        redirect_uri: str,
        scopes: list[str],
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes

    def build_install_url(
        self,
        *,
        shop_domain: str,
        state: str,
    ) -> str:
        shop_domain = self.normalize_shop_domain(shop_domain)

        query = urlencode(
            {
                "client_id": self.api_key,
                "scope": ",".join(self.scopes),
                "redirect_uri": self.redirect_uri,
                "state": state,
            }
        )

        return f"https://{shop_domain}/admin/oauth/authorize?{query}"

    def verify_hmac(self, *, params: dict[str, str]) -> bool:
        received_hmac = params.get("hmac")

        if not received_hmac:
            return False

        filtered = {
            key: value
            for key, value in params.items()
            if key not in {"hmac", "signature"}
        }

        message = "&".join(f"{key}={filtered[key]}" for key in sorted(filtered))

        digest = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(digest, received_hmac)

    async def exchange_code_for_access_token(
        self,
        *,
        shop_domain: str,
        code: str,
    ) -> dict:
        shop_domain = self.normalize_shop_domain(shop_domain)

        url = f"https://{shop_domain}/admin/oauth/access_token"

        try:
            async with httpx.AsyncClient(
                timeout=20,
            ) as client:
                response = await client.post(
                    url,
                    json={
                        "client_id": self.api_key,
                        "client_secret": self.api_secret,
                        "code": code,
                    },
                    headers={
                        "Accept": "application/json",
                    },
                )
        except httpx.TimeoutException as exc:
            raise IntegrationTimeoutError("Shopify OAuth request timed out") from exc
        except httpx.RequestError as exc:
            raise IntegrationUnavailableError(
                "Shopify OAuth transport is unavailable"
            ) from exc

        status_code = response.status_code

        if status_code == 429 or 500 <= status_code <= 599:
            raise IntegrationUnavailableError(
                f"Shopify OAuth is temporarily unavailable (status={status_code})"
            )

        if status_code >= 400:
            raise IntegrationProviderError(
                f"Shopify OAuth request failed (status={status_code})"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise IntegrationProviderError(
                "Shopify OAuth returned invalid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise IntegrationProviderError(
                "Shopify OAuth returned an unexpected payload"
            )

        return payload

    def validate_granted_scopes(self, raw_scopes: str | None) -> set[str]:
        granted = {
            scope.strip() for scope in (raw_scopes or "").split(",") if scope.strip()
        }
        # Shopify treats every write scope as also granting the corresponding
        # read scope, and OAuth responses may return only the write handle.
        # Expand the effective permissions before validating our required set.
        effective = set(granted)
        for scope in tuple(granted):
            if scope.startswith("write_"):
                effective.add("read_" + scope.removeprefix("write_"))
        required = set(self.scopes)
        if not required.issubset(effective):
            missing = sorted(required - effective)
            raise IntegrationProviderError(
                "Shopify did not grant required scopes: " + ", ".join(missing)
            )
        return effective

    async def register_compliance_webhooks(
        self,
        *,
        shop_domain: str,
        access_token: str,
        api_version: str,
    ) -> None:
        callback = urlsplit(self.redirect_uri)
        webhook_uri = (
            f"{callback.scheme}://{callback.netloc}/customer-service/shopify/webhooks"
        )
        url = (
            f"https://{self.normalize_shop_domain(shop_domain)}"
            f"/admin/api/{api_version}/graphql.json"
        )
        # Privacy/compliance topics (customers/data_request, customers/redact,
        # shop/redact) are configured as app compliance topics, not through
        # this Admin GraphQL enum. Register only ordinary app lifecycle topics
        # here; the same endpoint handles compliance deliveries once Shopify
        # has them configured for the app.
        topics = (
            "APP_UNINSTALLED",
            "APP_SUBSCRIPTIONS_UPDATE",
        )
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                for topic in topics:
                    response = await client.post(
                        url,
                        json={
                            "query": """
                                mutation RegisterWebhook(
                                  $topic: WebhookSubscriptionTopic!,
                                  $callbackUrl: URL!
                                ) {
                                  webhookSubscriptionCreate(
                                    topic: $topic,
                                    webhookSubscription: {
                                      callbackUrl: $callbackUrl,
                                      format: JSON
                                    }
                                  ) {
                                    webhookSubscription { id topic }
                                    userErrors { field message }
                                  }
                                }
                            """,
                            "variables": {
                                "topic": topic,
                                "callbackUrl": webhook_uri,
                            },
                        },
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                            "X-Shopify-Access-Token": access_token,
                        },
                    )
                    if response.status_code >= 400:
                        raise IntegrationProviderError(
                            "Shopify webhook registration failed "
                            f"(status={response.status_code})"
                        )
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        raise IntegrationProviderError(
                            "Shopify webhook registration returned invalid JSON"
                        ) from exc
                    if payload.get("errors"):
                        raise IntegrationProviderError(
                            "Shopify webhook registration failed: "
                            + "; ".join(
                                str(item.get("message"))
                                for item in payload["errors"]
                            )
                        )
                    result = (
                        (payload.get("data") or {}).get("webhookSubscriptionCreate")
                        or {}
                    )
                    if result.get("userErrors"):
                        messages = [
                            str(item.get("message"))
                            for item in result["userErrors"]
                        ]
                        # Reconnects may encounter subscriptions created by a
                        # previous partially completed OAuth callback.
                        duplicate_only = all(
                            any(
                                marker in message.lower()
                                for marker in (
                                    "already exists",
                                    "already been taken",
                                    "only one webhook subscription",
                                )
                            )
                            for message in messages
                        )
                        if not duplicate_only:
                            raise IntegrationProviderError(
                                "Shopify webhook registration failed: "
                                + "; ".join(messages)
                            )
        except httpx.TimeoutException as exc:
            raise IntegrationTimeoutError(
                "Shopify webhook registration timed out"
            ) from exc
        except httpx.RequestError as exc:
            raise IntegrationUnavailableError(
                "Shopify webhook registration transport is unavailable"
            ) from exc

    def normalize_shop_domain(self, shop_domain: str) -> str:
        value = (shop_domain or "").strip().lower()
        value = value.replace("https://", "").replace("http://", "").rstrip("/")

        if not value.endswith(".myshopify.com"):
            value = f"{value}.myshopify.com"

        if not SHOP_DOMAIN_PATTERN.fullmatch(value):
            raise ValueError("Invalid Shopify shop domain")

        return value
