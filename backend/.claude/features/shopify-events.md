# Feature: Shopify Events

## Spec
- **What it should do:** React to important Shopify changes (new order, order updated, fulfillment updated, refund, customer updated) without manual initiation.
- **Layer:** provider
- **Likely location (guess — verify, I don't have your repo):** providers/shopify/webhooks
- **Key entities:** Webhook event, Event record (id, type, workspace, status, timestamp, failure info)
- **Core rules to check against:** Webhook authenticity verified; events tenant-scoped; duplicate events handled safely; processing idempotent; invalid events don't trigger actions; failures observable

## Acceptance criteria (from the v1 spec's "DONE" list)
- All required v1 events received and verified
- Tenant resolved correctly
- Duplicate delivery is safe (idempotent)
- Events persisted/processed; failures observable
- Events can trigger supported automation

## Production success condition
> A real Shopify event can safely enter Tajeran and trigger the correct tenant-scoped behavior exactly once from Tajeran's business perspective.

## Audit Result
_Filled in by `/audit-feature shopify-events`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- **ShopifyWebhookReceipt** model (`app/domains/customer_service/models/shopify.py`) — webhook_id (unique), shop_domain, topic, status, payload (JSONB), processed_at
- **Webhook HMAC verification** (`app/domains/customer_service/integrations/shopify/lifecycle.py::verify_webhook_hmac()`) — validates X-Shopify-Hmac-SHA256 header with base64(HMAC-SHA256)
- **Webhook endpoint** (`app/api/products/customer_service/providers/shopify.py::shopify_compliance_webhook()`) — receives POST, verifies HMAC, delegates to process_compliance_webhook()
- **ShopifyWebhookAdapter** (`app/domains/customer_service/integrations/shopify/webhooks.py`) — minimal adapter class (needs implementation review)

**Is it good enough?**
- **Partially.** Webhook receipt + HMAC verification exist; topic-specific processing unclear.
  - ✓ Webhook authenticity verified (HMAC)
  - ✓ Events persisted (ShopifyWebhookReceipt)
  - ✓ Status tracked
  - ⚠️ **Event processing unclear:** ShopifyWebhookAdapter minimal; no evidence of order_updated, fulfillment_updated, customer_updated handlers
  - ⚠️ **Idempotency:** webhook_id unique but unclear if re-delivery with same ID is caught + silently ignored
  - ⚠️ **Tenant resolution missing:** webhook_receipt has shop_domain but no workspace_id; cannot scope processing to correct tenant
  - ⚠️ **Automation triggering:** no clear link from event to customer service automation

**Gaps / risks:**
- **Missing event handlers:** Spec lists v1 events (new order, order updated, fulfillment updated, refund, customer updated). Only receipt + HMAC found; no explicit handlers.
- **Idempotency not enforced:** webhook_id unique but no test/guard for duplicate receipt with same ID → ensure processed only once.
- **Tenant resolution broken:** webhook_receipt.shop_domain indexed but not workspace_id. Cannot route event to correct workspace → all workspaces will try to process all shops' webhooks.
- **Failure observability weak:** status field exists but no retry logic, DLQ, or monitoring for failed webhooks.
- **No automation linkage:** Spec says "events can trigger supported automation" but no evidence of workflow/automation invocation on webhook.

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] **Implement event handlers:** Extend ShopifyWebhookAdapter in `app/domains/customer_service/integrations/shopify/webhooks.py` with methods: `async def on_order_created()`, `async def on_order_updated()`, `async def on_fulfillment_updated()`, `async def on_order_refunded()`, `async def on_customer_updated()`. Each delegates to relevant business logic.
- [ ] **Add idempotency guard:** Modify `shopify_compliance_webhook()` endpoint in `app/api/products/customer_service/providers/shopify.py` to check if ShopifyWebhookReceipt.webhook_id already exists before processing. Return 202 immediately if already processed (idempotent).
- [ ] **Add workspace_id to webhook receipt:** Add `workspace_id: UUID | None` column to ShopifyWebhookReceipt in `app/domains/customer_service/models/shopify.py`. Resolve from shop_domain → connection.workspace_id during webhook processing. Query/filter by workspace_id to prevent cross-tenant leaks.
- [ ] **Add failure handling:** Add `failure_reason: str | None` and `retry_count: int` columns to ShopifyWebhookReceipt. Implement retry logic in background job that reprocesses status='failed' receipts (exponential backoff, max 5 retries).
- [ ] **Link events to automation:** Call workflow/automation trigger on successful webhook processing (e.g., on order_updated, trigger order change automation). Update `process_compliance_webhook()` to emit automation event or call automation service.
- [ ] **Test idempotency:** Add test in `tests/customer_service/shopify/test_shopify_webhook_idempotency.py` that sends same webhook_id twice, verifies second returns 202 and no duplicate processing occurs.
- [ ] **Test tenant isolation:** Add test that sends webhook for shop in workspace A, verifies only workspace A's automation is triggered (not other workspaces). 
