# Feature: Shopify Commerce Context

## Spec
- **What it should do:** Retrieve accurate, current Shopify context (customer, order, product, fulfillment, tracking, return, refund) relevant to a conversation.
- **Layer:** provider
- **Likely location (guess — verify, I don't have your repo):** providers/shopify/capabilities (get_customer, get_order, get_product, get_fulfillment, get_tracking, get_return, get_refund)
- **Key entities:** Customer, Order, Product, Variant, Fulfillment, Shipment, Tracking, Return, Refund
- **Core rules to check against:** Every request tenant-scoped; Shopify credentials stay inside provider/capability boundary; AI receives only relevant context; missing data represented explicitly; stale data not presented as current without indication

## Acceptance criteria (from the v1 spec's "DONE" list)
- Customer/order/product/variant/fulfillment/tracking/return/refund retrieval all work
- Tenant isolation enforced
- Errors represented safely
- AI can consume normalized context
- Tests cover provider failures and isolation

## Production success condition
> Tajeran can reliably retrieve the commerce context required to answer a real customer-service request.

## Audit Result
_Filled in by `/audit-feature shopify-commerce-context`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- **ShopifyRealProvider** (`app/domains/customer_service/integrations/shopify/real_provider.py`) — implements: get_order(order_ref), get_shipping_status(tracking_number), refund_order(), cancel_order(), change_order_address(), reship_order(), report_damaged_item(), verify_connection()
- **CustomerSupportCommerceContextService** (`app/domains/customer_service/services/support/commerce/customer_support_commerce_context.py`) — wraps capability resolution for `ecommerce.orders.get` with user_id scoping
- **CommerceOrderAdapterRegistry** — normalizes orders across Shopify and other providers
- **Caching** — CustomerServiceShopifyOrderCache (order_id indexed) and CustomerServiceShippingTrackingCache
- **Error handling** — result.ok checks, error_message propagation
- **Tests** — some Shopify provider tests exist

**Is it good enough?**
- **Partially.** Order + shipping retrieval work; tenant scoped via user_id in capability invocation.
  - ✓ Order retrieval works (get_order_by_name/id, caching)
  - ✓ Shipping/tracking retrieval works (get_shipping_status)
  - ✓ Refund, cancel, reship operations mapped to commerce context
  - ✓ Tenant isolation via user_id in CapabilityInvocation
  - ✓ Error handling (result.ok checks)
  - ✓ Tests cover provider failures
  - ⚠️ **Incomplete entity coverage:** missing explicit customer, product, variant, fulfillment, return context retrieval. Only order/tracking found.
  - ⚠️ **Stale data not indicated:** caches lack timestamps; no indication if data is fresh or stale
  - ⚠️ **Tenant isolation not comprehensively tested:** no cross-tenant leakage test

**Gaps / risks:**
- **Missing entity retrieval:** Spec lists Customer, Product, Variant, Fulfillment, Return as v1 entities. Only Order and Tracking/Shipping found in provider. No get_customer(), get_product(), get_fulfillment(), get_return() methods.
- **Stale data not marked:** CustomerServiceShopifyOrderCache and ShippingTrackingCache store payload but no created_at/staleness indication. AI cannot distinguish "data is 1 hour old" from "data is current."
- **Missing data representation unclear:** Spec says "missing data represented explicitly." No test or pattern for null/missing fields (e.g., order found but no fulfillment info).
- **Tenant isolation not tested:** No test verifying user from workspace A cannot access workspace B's commerce context via capability resolution.
- **Credential boundary unclear:** ShopifyRealProvider takes access_token; need to verify no credential leakage to capability output.

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] **Add missing entity retrievers:** Add methods to ShopifyRealProvider in `app/domains/customer_service/integrations/shopify/real_provider.py`: `async def get_customer()`, `async def get_product()`, `async def get_fulfillment()`, `async def get_return()`. Each queries Shopify GraphQL and returns normalized entity or raises IntegrationProviderError.
- [ ] **Mark cache staleness:** Add `retrieved_at: datetime` column to CustomerServiceShopifyOrderCache and CustomerServiceShippingTrackingCache in `app/domains/customer_service/models/shopify.py`. Include in response schemas so AI knows data age.
- [ ] **Missing data handling:** Add test in `tests/customer_service/shopify/test_shopify_commerce_context_missing_data.py` that verifies: (1) order found, fulfillment missing → returns {order, fulfillment: null}, (2) order not found → returns {found: false}.
- [ ] **Tenant isolation test:** Add test in `tests/customer_service/shopify/test_shopify_commerce_context_tenant_isolation.py` that: (1) user A in workspace X calls get_order(), (2) user B in workspace Y attempts to access user A's order via capability, (3) verifies 403 or user B gets only their own data.
- [ ] **Credential isolation audit:** Verify ShopifyRealProvider.get_order() and peers do not leak access_token in CapabilityResult.output. Check `execute_shopify_get_order()` in `app/runtime/capabilities/execution/providers/shopify.py` that output is sanitized (order data only, no token).
- [ ] **Comprehensive entity test:** Add test in `tests/customer_service/shopify/test_shopify_commerce_context_all_entities.py` covering customer, order, product, variant, fulfillment, tracking, return retrieval with success and failure cases. 
