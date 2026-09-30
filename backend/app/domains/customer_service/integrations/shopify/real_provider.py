from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.integrations.errors import (
    IntegrationProviderError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)


class RealShopifyProvider:
    requires_durable_approval = True

    def __init__(
        self,
        *,
        api_version: str | None = None,
        timeout_seconds: float = 20.0,
    ):
        self.api_version = api_version or settings.SHOPIFY_API_VERSION
        self.timeout_seconds = timeout_seconds

    async def verify_connection(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
    ) -> dict:
        self._require_access_token(access_token)

        payload = await self._graphql_request(
            shop_domain=shop_domain,
            access_token=access_token,
            query="""
                query VerifyShop {
                  shop { id name myshopifyDomain primaryDomain { url } }
                }
            """,
        )

        raw_shop = (payload.get("data") or {}).get("shop") or {}
        shop = {
            "id": raw_shop.get("id"),
            "name": raw_shop.get("name"),
            "myshopify_domain": raw_shop.get("myshopifyDomain"),
            "primary_domain": (raw_shop.get("primaryDomain") or {}).get("url"),
        }

        if not isinstance(shop, dict):
            raise HTTPException(
                status_code=502,
                detail=("Shopify verification response did not contain shop data"),
            )

        return shop

    async def get_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order_ref: str,
    ) -> dict | None:
        self._require_access_token(access_token)

        normalized = self._normalize_order_ref(order_ref)
        lookup = normalized["with_hash"]
        if normalized["without_hash"].isdigit():
            lookup = f"name:{normalized['with_hash']} OR id:{normalized['without_hash']}"
        payload = await self._graphql_request(
            shop_domain=shop_domain,
            access_token=access_token,
            query="""
                query FindOrder($query: String!) {
                  orders(first: 1, query: $query) {
                    nodes {
                      id name createdAt email displayFinancialStatus displayFulfillmentStatus
                      currentTotalPriceSet { shopMoney { amount currencyCode } }
                      customer { id email firstName lastName }
                      lineItems(first: 100) { nodes { id quantity title variant { id title sku } } }
                      fulfillments {
                        id status createdAt
                        trackingInfo { number url company }
                      }
                      transactions {
                        id kind status gateway amountSet { shopMoney { amount currencyCode } }
                      }
                    }
                  }
                }
            """,
            variables={"query": lookup},
        )
        nodes = ((payload.get("data") or {}).get("orders") or {}).get("nodes") or []
        if nodes:
            return self._normalize_graphql_order(nodes[0], shop_domain=shop_domain)

        # Development stores commonly contain draft orders but no paid Orders.
        # Keep the customer-service order contract stable while exposing those
        # records as read-only commerce context.
        draft_payload = await self._graphql_request(
            shop_domain=shop_domain,
            access_token=access_token,
            query="""
                query FindDraftOrder($query: String!) {
                  draftOrders(first: 1, query: $query) {
                    nodes {
                      id name createdAt email status
                      totalPriceSet { shopMoney { amount currencyCode } }
                      customer { id email firstName lastName }
                      lineItems(first: 100) {
                        nodes { id quantity name variant { id title sku } }
                      }
                    }
                  }
                }
            """,
            variables={"query": lookup},
        )
        draft_nodes = (
            ((draft_payload.get("data") or {}).get("draftOrders") or {}).get("nodes")
            or []
        )
        if not draft_nodes:
            return None
        return self._normalize_graphql_draft_order(
            draft_nodes[0], shop_domain=shop_domain
        )

    async def list_knowledge_content(
        self, *, shop_domain: str, access_token: str | None
    ) -> list[dict]:
        self._require_access_token(access_token)
        payload = await self._graphql_request(
            shop_domain=shop_domain,
            access_token=access_token,
            query="""
                query CustomerServiceKnowledge {
                  pages(first: 100) {
                    nodes { id title body updatedAt onlineStoreUrl }
                  }
                  shop {
                    privacyPolicy { title body url }
                    refundPolicy { title body url }
                    shippingPolicy { title body url }
                    termsOfService { title body url }
                  }
                }
            """,
        )
        data = payload.get("data") or {}
        items = [
            {
                "kind": "shopify_page",
                "external_id": page["id"],
                "title": page.get("title") or "Shopify page",
                "content": page.get("body") or "",
                "url": page.get("onlineStoreUrl"),
                "meta": {"updated_at": page.get("updatedAt")},
            }
            for page in ((data.get("pages") or {}).get("nodes") or [])
            if (page.get("body") or "").strip()
        ]
        for key, policy in (data.get("shop") or {}).items():
            if isinstance(policy, dict) and (policy.get("body") or "").strip():
                items.append(
                    {
                        "kind": "shopify_policy",
                        "external_id": f"policy:{key}",
                        "title": policy.get("title") or key,
                        "content": policy["body"],
                        "url": policy.get("url"),
                        "meta": {"policy_type": key},
                    }
                )
        return items

    async def create_app_subscription(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        name: str,
        amount: str,
        currency: str,
        interval: str,
        return_url: str,
        trial_days: int,
        test: bool,
    ) -> dict:
        self._require_access_token(access_token)
        payload = await self._graphql_request(
            shop_domain=shop_domain,
            access_token=access_token,
            query="""
                mutation CreateAppSubscription(
                  $name: String!, $lineItems: [AppSubscriptionLineItemInput!]!,
                  $returnUrl: URL!, $trialDays: Int, $test: Boolean
                ) {
                  appSubscriptionCreate(
                    name: $name, lineItems: $lineItems, returnUrl: $returnUrl,
                    trialDays: $trialDays, test: $test,
                    replacementBehavior: STANDARD
                  ) {
                    appSubscription { id name status test }
                    confirmationUrl
                    userErrors { field message }
                  }
                }
            """,
            variables={
                "name": name,
                "returnUrl": return_url,
                "trialDays": trial_days,
                "test": test,
                "lineItems": [
                    {
                        "plan": {
                            "appRecurringPricingDetails": {
                                "price": {"amount": amount, "currencyCode": currency},
                                "interval": interval,
                            }
                        }
                    }
                ],
            },
        )
        result = (payload.get("data") or {}).get("appSubscriptionCreate") or {}
        self._raise_graphql_user_errors(result, operation="subscription creation")
        subscription = result.get("appSubscription") or {}
        confirmation_url = result.get("confirmationUrl")
        if not subscription.get("id") or not confirmation_url:
            raise IntegrationProviderError(
                "Shopify did not return billing confirmation"
            )
        return {"id": subscription["id"], "confirmation_url": confirmation_url}

    async def get_active_app_subscriptions(
        self, *, shop_domain: str, access_token: str | None
    ) -> list[dict]:
        self._require_access_token(access_token)
        payload = await self._graphql_request(
            shop_domain=shop_domain,
            access_token=access_token,
            query="""
                query ActiveAppSubscriptions {
                  currentAppInstallation {
                    activeSubscriptions {
                      id name status test trialDays currentPeriodEnd
                    }
                  }
                }
            """,
        )
        installation = (payload.get("data") or {}).get("currentAppInstallation") or {}
        return list(installation.get("activeSubscriptions") or [])

    async def cancel_app_subscription(
        self, *, shop_domain: str, access_token: str | None, subscription_id: str
    ) -> dict:
        self._require_access_token(access_token)
        payload = await self._graphql_request(
            shop_domain=shop_domain,
            access_token=access_token,
            query="""
                mutation CancelAppSubscription($id: ID!) {
                  appSubscriptionCancel(id: $id, prorate: false) {
                    appSubscription { id name status }
                    userErrors { field message }
                  }
                }
            """,
            variables={"id": subscription_id},
        )
        result = (payload.get("data") or {}).get("appSubscriptionCancel") or {}
        self._raise_graphql_user_errors(result, operation="subscription cancellation")
        subscription = result.get("appSubscription") or {}
        if not subscription.get("id"):
            raise IntegrationProviderError(
                "Shopify did not return canceled subscription"
            )
        return subscription

    @staticmethod
    def _raise_graphql_user_errors(result: dict, *, operation: str) -> None:
        errors = result.get("userErrors") or []
        if errors:
            raise IntegrationProviderError(
                f"Shopify {operation} failed: "
                + "; ".join(str(item.get("message")) for item in errors)
            )

    async def refund_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        reason: str | None,
        amount: str | None,
        scope: dict | None = None,
    ) -> dict:
        self._require_access_token(access_token)

        order_id = order.get("id")
        if not order_id:
            raise HTTPException(status_code=422, detail="Shopify order id is missing")
        order_id = self._as_shopify_gid(order_id, "Order")

        refund_scope = self._validate_refund_scope(order=order, amount=amount, scope=scope)
        transaction = next(
            (item for item in (order.get("transactions") or []) if item.get("id")),
            None,
        )
        if transaction is None:
            raise IntegrationProviderError("Shopify order has no refundable transaction")
        currency = refund_scope["currency"]
        result = await self._graphql_request(
            shop_domain=shop_domain,
            access_token=access_token,
            query="""
                mutation CreateRefund($input: RefundInput!) {
                  refundCreate(input: $input) {
                    refund { id createdAt }
                    userErrors { field message }
                  }
                }
            """,
            variables={
                "input": {
                    "orderId": order_id,
                    "notify": False,
                    "note": reason or "Approved customer-service refund",
                    "refundLineItems": [
                        {
                            "lineItemId": self._as_shopify_gid(
                                item["line_item_id"], "LineItem"
                            ),
                            "quantity": item["quantity"],
                            "restockType": str(item["restock_type"]).upper(),
                        }
                        for item in refund_scope["refund_line_items"]
                    ],
                    "transactions": [{
                        "parentId": transaction["id"],
                        "amount": str(refund_scope["amount"]),
                        "gateway": transaction.get("gateway"),
                    }],
                }
            },
        )
        mutation = (result.get("data") or {}).get("refundCreate") or {}
        self._raise_graphql_user_errors(mutation, operation="refund creation")
        refund = mutation.get("refund") or {}
        if not refund.get("id"):
            raise IntegrationProviderError("Shopify did not return the created refund")
        return {
            "status": "refunded",
            "message": "Shopify refund created.",
            "reason": reason,
            "amount": str(refund_scope["amount"]),
            "currency": currency,
            "scope": refund_scope["scope"],
            "shop_domain": shop_domain,
            "order_id": str(order_id),
            "order_name": order.get("name"),
            "financial_status": order.get("financial_status"),
            "refund_id": str(refund["id"]),
            "payload": refund,
        }

    async def cancel_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        reason: str | None,
    ) -> dict:
        self._require_access_token(access_token)

        fulfillment_status = order.get("fulfillment_status")
        cancelled_at = order.get("cancelled_at")

        if cancelled_at:
            return {
                "status": "blocked",
                "message": "Order is already cancelled.",
                "reason": reason,
                "shop_domain": shop_domain,
                "order_id": str(order.get("id")),
                "order_name": order.get("name"),
            }

        if fulfillment_status == "fulfilled":
            return {
                "status": "blocked",
                "message": "Order is fulfilled. Cancel is blocked for safety.",
                "reason": reason,
                "shop_domain": shop_domain,
                "order_id": str(order.get("id")),
                "order_name": order.get("name"),
            }

        order_id = order.get("id")
        if not order_id:
            raise HTTPException(status_code=422, detail="Shopify order id is missing")

        result = await self._graphql_request(
            shop_domain=shop_domain,
            access_token=access_token,
            query="""
                mutation CancelOrder($orderId: ID!, $reason: OrderCancelReason) {
                  orderCancel(orderId: $orderId, reason: $reason, notifyCustomer: false, restock: false) {
                    job { id done }
                    orderCancelUserErrors { field message code }
                  }
                }
            """,
            variables={
                "orderId": self._as_shopify_gid(order_id, "Order"),
                "reason": "CUSTOMER",
            },
        )
        mutation = (result.get("data") or {}).get("orderCancel") or {}
        errors = mutation.get("orderCancelUserErrors") or []
        if errors:
            raise IntegrationProviderError(
                "Shopify cancellation failed: "
                + "; ".join(str(item.get("message")) for item in errors)
            )
        payload = mutation.get("job") or {}

        return {
            "status": "cancelled",
            "message": "Shopify order cancelled.",
            "reason": reason,
            "shop_domain": shop_domain,
            "order_id": str(order_id),
            "order_name": order.get("name"),
            "payload": payload,
        }

    async def change_order_address(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        new_address: dict,
        note: str | None,
    ) -> dict:
        raise IntegrationProviderError(
            "Shipping-address updates are intentionally disabled in V1; "
            "use human support outside Shopify until the GraphQL contract is certified."
        )

    async def reship_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        reason: str | None,
        note: str | None,
        scope: dict | None = None,
    ) -> dict:
        self._require_access_token(access_token)

        replacement = self._validate_replacement_scope(order=order, scope=scope)
        original_order_id = order.get("admin_graphql_api_id") or (
            f"gid://shopify/Order/{order.get('id')}"
        )
        address = (scope or {}).get("new_address") or order.get("shipping_address")
        draft_input: dict[str, Any] = {
            "lineItems": [
                {
                    "variantId": replacement["variant_id"],
                    "quantity": replacement["quantity"],
                }
            ],
            "note": note or reason or "Approved customer-service replacement",
            "tags": [
                "tajeran-replacement",
                f"source-order:{order.get('name') or order.get('id')}",
            ],
            "customAttributes": [
                {"key": "tajeran_source_order", "value": str(original_order_id)},
                {"key": "tajeran_reason", "value": reason or "replacement"},
            ],
        }
        if address:
            draft_input["shippingAddress"] = self._graphql_address(address)
        result = await self._graphql_request(
            shop_domain=shop_domain,
            access_token=access_token,
            query="""
                mutation CreateReplacementDraft($input: DraftOrderInput!) {
                  draftOrderCreate(input: $input) {
                    draftOrder { id name invoiceUrl status }
                    userErrors { field message }
                  }
                }
            """,
            variables={"input": draft_input},
        )
        mutation = (result.get("data") or {}).get("draftOrderCreate") or {}
        errors = mutation.get("userErrors") or []
        if errors:
            raise IntegrationProviderError(
                "Shopify rejected replacement draft: "
                + "; ".join(str(item.get("message")) for item in errors)
            )
        draft = mutation.get("draftOrder")
        if not isinstance(draft, dict) or not draft.get("id"):
            raise IntegrationProviderError("Shopify did not return a replacement draft")
        return {
            "status": "draft_created",
            "message": "Replacement draft order created for merchant review.",
            "reason": reason,
            "note": note,
            "scope": scope or {},
            "shop_domain": shop_domain,
            "order_id": str(order.get("id")),
            "order_name": order.get("name"),
            "replacement_strategy": "draft_order",
            "draft_order": draft,
        }

    async def report_damaged_item(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        reason: str | None,
        note: str | None,
    ) -> dict:
        self._require_access_token(access_token)

        return {
            "status": "prepared",
            "message": "Damaged item case prepared for support review.",
            "reason": reason,
            "note": note,
            "shop_domain": shop_domain,
            "order_id": str(order.get("id")),
            "order_name": order.get("name"),
        }

    async def get_shipping_status(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
    ) -> dict:
        self._require_access_token(access_token)

        fulfillments = order.get("fulfillments") or []
        tracking_number = None
        tracking_url = None
        tracking_company = None

        for fulfillment in fulfillments:
            tracking_number = tracking_number or fulfillment.get("tracking_number")
            tracking_url = tracking_url or fulfillment.get("tracking_url")
            tracking_company = tracking_company or fulfillment.get("tracking_company")

        return {
            "status": "found" if fulfillments else "not_found",
            "message": "Shipping status found"
            if fulfillments
            else "No fulfillment tracking found on Shopify order.",
            "fulfillment_status": order.get("fulfillment_status"),
            "tracking_number": tracking_number,
            "tracking_url": tracking_url,
            "tracking_company": tracking_company,
            "shop_domain": shop_domain,
            "order_id": str(order.get("id")),
            "order_name": order.get("name"),
        }

    async def add_order_note(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        note: str,
    ) -> dict:
        self._require_access_token(access_token)
        if not note.strip():
            raise HTTPException(status_code=422, detail="Order note is required")
        order_id = order.get("id")
        if not order_id:
            raise HTTPException(status_code=422, detail="Shopify order id is missing")
        result = await self._graphql_request(
            shop_domain=shop_domain,
            access_token=access_token,
            query="""
                mutation AddOrderNote($input: OrderInput!) {
                  orderUpdate(input: $input) {
                    order { id note }
                    userErrors { field message }
                  }
                }
            """,
            variables={
                "input": {
                    "id": self._as_shopify_gid(order_id, "Order"),
                    "note": note,
                }
            },
        )
        mutation = (result.get("data") or {}).get("orderUpdate") or {}
        self._raise_graphql_user_errors(mutation, operation="order note update")
        updated = mutation.get("order") or {}
        if not updated.get("id"):
            raise IntegrationProviderError("Shopify did not return the updated order")
        return {
            "status": "updated",
            "message": "Shopify order note added.",
            "order_id": str(updated["id"]),
            "order_name": order.get("name"),
            "note": updated.get("note"),
            "shop_domain": shop_domain,
        }

    async def _request(
        self,
        method: str,
        *,
        shop_domain: str,
        access_token: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict:
        shop_domain = self._normalize_shop_domain(shop_domain)
        url = f"https://{shop_domain}/admin/api/{self.api_version}{path}"

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
            ) as client:
                response = await client.request(
                    method,
                    url,
                    headers={
                        "X-Shopify-Access-Token": (access_token),
                        "Accept": "application/json",
                        "Content-Type": ("application/json"),
                    },
                    params=params,
                    json=json,
                )
        except httpx.TimeoutException as exc:
            raise IntegrationTimeoutError(
                "Shopify Admin API request timed out"
            ) from exc
        except httpx.RequestError as exc:
            raise IntegrationUnavailableError(
                "Shopify Admin API transport is unavailable"
            ) from exc

        status_code = response.status_code

        if status_code == 429:
            raise IntegrationUnavailableError(
                "Shopify Admin API rate limit exceeded",
                retry_after_seconds=(
                    self._retry_after_seconds(response.headers.get("Retry-After"))
                ),
            )

        if 500 <= status_code <= 599:
            raise IntegrationUnavailableError(
                f"Shopify Admin API is temporarily unavailable (status={status_code})"
            )

        if status_code >= 400:
            raise IntegrationProviderError(
                f"Shopify Admin API request failed (status={status_code})"
            )

        if not response.content:
            return {}

        try:
            payload = response.json()
        except ValueError as exc:
            raise IntegrationProviderError(
                "Shopify Admin API returned invalid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise IntegrationProviderError(
                "Shopify Admin API returned an unexpected payload"
            )

        return payload

    async def _graphql_request(
        self,
        *,
        shop_domain: str,
        access_token: str,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict:
        payload = await self._request(
            "POST",
            shop_domain=shop_domain,
            access_token=access_token,
            path="/graphql.json",
            json={"query": query, "variables": variables or {}},
        )
        errors = payload.get("errors") or []
        if errors:
            raise IntegrationProviderError(
                "Shopify GraphQL request failed: "
                + "; ".join(str(item.get("message")) for item in errors)
            )
        return payload

    @staticmethod
    def _as_shopify_gid(value: Any, resource: str) -> str:
        text = str(value)
        return text if text.startswith("gid://shopify/") else f"gid://shopify/{resource}/{text}"

    @classmethod
    def _normalize_graphql_order(cls, node: dict, *, shop_domain: str) -> dict:
        money = ((node.get("currentTotalPriceSet") or {}).get("shopMoney") or {})
        customer = node.get("customer") or {}
        fulfillments = []
        raw_fulfillments = node.get("fulfillments") or []
        if isinstance(raw_fulfillments, dict):
            raw_fulfillments = raw_fulfillments.get("nodes") or []
        for fulfillment in raw_fulfillments:
            tracking = (fulfillment.get("trackingInfo") or [{}])[0]
            fulfillments.append(
                {
                    "id": fulfillment.get("id"),
                    "status": str(fulfillment.get("status") or "").lower(),
                    "tracking_number": tracking.get("number"),
                    "tracking_url": tracking.get("url"),
                    "tracking_company": tracking.get("company"),
                }
            )
        return {
            "id": node.get("id"),
            "admin_graphql_api_id": node.get("id"),
            "name": node.get("name"),
            "created_at": node.get("createdAt"),
            "email": node.get("email") or customer.get("email"),
            "customer": customer,
            "currency": money.get("currencyCode"),
            "total_price": money.get("amount"),
            "financial_status": str(node.get("displayFinancialStatus") or "").lower(),
            "fulfillment_status": str(node.get("displayFulfillmentStatus") or "").lower(),
            "line_items": [
                {
                    "id": item.get("id"),
                    "quantity": item.get("quantity"),
                    "title": item.get("title"),
                    "variant_id": (item.get("variant") or {}).get("id"),
                }
                for item in ((node.get("lineItems") or {}).get("nodes") or [])
            ],
            "fulfillments": fulfillments,
            "transactions": [
                {
                    "id": tx.get("id"),
                    "kind": str(tx.get("kind") or "").lower(),
                    "status": str(tx.get("status") or "").lower(),
                    "gateway": tx.get("gateway"),
                }
                for tx in (
                    (node.get("transactions") or {}).get("nodes")
                    if isinstance(node.get("transactions"), dict)
                    else (node.get("transactions") or [])
                )
                if str(tx.get("status") or "").upper() == "SUCCESS"
            ],
            "shop_domain": shop_domain,
        }

    @classmethod
    def _normalize_graphql_draft_order(cls, node: dict, *, shop_domain: str) -> dict:
        money = ((node.get("totalPriceSet") or {}).get("shopMoney") or {})
        customer = node.get("customer") or {}
        return {
            "id": node.get("id"),
            "admin_graphql_api_id": node.get("id"),
            "name": node.get("name"),
            "created_at": node.get("createdAt"),
            "email": node.get("email") or customer.get("email"),
            "customer": customer,
            "currency": money.get("currencyCode"),
            "total_price": money.get("amount"),
            "financial_status": "pending",
            "fulfillment_status": "unfulfilled",
            "line_items": [
                {
                    "id": item.get("id"),
                    "quantity": item.get("quantity"),
                    "title": item.get("name"),
                    "variant_id": (item.get("variant") or {}).get("id"),
                }
                for item in ((node.get("lineItems") or {}).get("nodes") or [])
            ],
            "fulfillments": [],
            "transactions": [],
            "draft_order_status": str(node.get("status") or "").lower(),
            "shop_domain": shop_domain,
        }

    def _validate_refund_scope(
        self, *, order: dict, amount: str | None, scope: dict | None
    ) -> dict:
        if not amount:
            raise HTTPException(status_code=422, detail="Refund amount is required")
        requested = self._money(amount, field="refund amount")
        if requested <= 0:
            raise HTTPException(
                status_code=422, detail="Refund amount must be positive"
            )
        provided = scope or {}
        scoped_items = provided.get("line_items") or []
        if not scoped_items:
            raise HTTPException(
                status_code=422,
                detail="Refund line items and restock behavior are required",
            )
        order_items = {
            str(item.get("id")): item for item in order.get("line_items") or []
        }
        normalized = []
        seen: set[str] = set()
        for item in scoped_items:
            item_id = str(item.get("line_item_id") or "")
            order_item = order_items.get(item_id)
            if not order_item or item_id in seen:
                raise HTTPException(
                    status_code=422, detail=f"Invalid refund line item: {item_id}"
                )
            seen.add(item_id)
            quantity = int(item.get("quantity") or 0)
            if quantity < 1 or quantity > int(order_item.get("quantity") or 0):
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid refund quantity for line item {item_id}",
                )
            restock_type = item.get("restock_type") or "no_restock"
            if restock_type not in {"no_restock", "cancel", "return"}:
                raise HTTPException(
                    status_code=422, detail="Invalid Shopify restock type"
                )
            normalized.append(
                {
                    "line_item_id": int(item_id) if item_id.isdigit() else item_id,
                    "quantity": quantity,
                    "restock_type": restock_type,
                }
            )
        currency = str(provided.get("currency") or order.get("currency") or "").upper()
        if len(currency) != 3:
            raise HTTPException(status_code=422, detail="Refund currency is required")
        order_currency = str(order.get("currency") or "").upper()
        if order_currency and currency != order_currency:
            raise HTTPException(
                status_code=422, detail="Refund currency must match the order"
            )
        return {
            "amount": requested,
            "currency": currency,
            "refund_line_items": normalized,
            "scope": {**provided, "currency": currency},
        }

    def _validate_replacement_scope(self, *, order: dict, scope: dict | None) -> dict:
        provided = scope or {}
        item_id = str(provided.get("replacement_line_item_id") or "")
        quantity = int(provided.get("replacement_quantity") or 0)
        if not item_id or quantity < 1:
            raise HTTPException(
                status_code=422,
                detail="Replacement line item and quantity are required",
            )
        item = next(
            (
                candidate
                for candidate in order.get("line_items") or []
                if str(candidate.get("id")) == item_id
            ),
            None,
        )
        if not item or quantity > int(item.get("quantity") or 0):
            raise HTTPException(status_code=422, detail="Invalid replacement scope")
        variant_id = item.get("variant_id")
        if not variant_id:
            raise HTTPException(
                status_code=422, detail="Replacement item has no Shopify variant"
            )
        return {
            "quantity": quantity,
            "variant_id": str(variant_id)
            if str(variant_id).startswith("gid://")
            else f"gid://shopify/ProductVariant/{variant_id}",
        }

    @staticmethod
    def _graphql_address(address: dict) -> dict:
        mapping = {
            "first_name": "firstName",
            "last_name": "lastName",
            "address1": "address1",
            "address2": "address2",
            "city": "city",
            "province": "province",
            "country": "country",
            "zip": "zip",
            "phone": "phone",
            "company": "company",
        }
        return {
            target: address[source]
            for source, target in mapping.items()
            if address.get(source)
        }

    @staticmethod
    def _money(value: Any, *, field: str) -> Decimal:
        try:
            return Decimal(str(value)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            raise HTTPException(status_code=422, detail=f"Invalid {field}") from None

    @staticmethod
    def _retry_after_seconds(
        raw: str | None,
    ) -> float | None:
        if raw is None:
            return None

        try:
            value = float(raw.strip())
        except (TypeError, ValueError):
            return None

        if value < 0:
            return None

        # Provider-controlled Retry-After must not
        # create an unbounded worker/request sleep.
        return min(value, 30.0)

    def _require_access_token(self, access_token: str | None) -> None:
        if not access_token:
            raise HTTPException(
                status_code=401,
                detail="Shopify access token is required for real provider",
            )

    def _normalize_order_ref(self, order_ref: str) -> dict[str, str]:
        value = str(order_ref or "").strip()
        without_hash = value.lstrip("#")
        with_hash = value if value.startswith("#") else f"#{value}"

        return {
            "raw": value,
            "without_hash": without_hash,
            "with_hash": with_hash,
        }

    def _normalize_shop_domain(self, shop_domain: str) -> str:
        value = str(shop_domain or "").strip().lower()
        value = value.replace("https://", "").replace("http://", "").rstrip("/")

        if not value.endswith(".myshopify.com"):
            value = f"{value}.myshopify.com"

        return value
