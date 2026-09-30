# Feature: Customer Profile

## Spec
- **What it should do:** A useful Customer 360 view (identity, orders, fulfillment, refunds, returns, previous conversations, tags) directly beside the conversation.
- **Layer:** product
- **Likely location (guess — verify, I don't have your repo):** domains/customer_service/customer_profile (aggregates provider Shopify data + internal conversation history)
- **Key entities:** Customer, Customer Identity, Order, Conversation, Ticket, Refund, Return, Tag
- **Core rules to check against:** Customer data tenant-scoped; identity matching avoids unsafe merges; commerce data reflects Shopify source of truth where appropriate; sensitive info appropriately protected

## Acceptance criteria (from the v1 spec's "DONE" list)
- Identity, orders, order value, last order, fulfillment, refunds/returns, previous conversations, tags all displayed
- Tenant isolation works

## Production success condition
> An agent can understand who the customer is and their relevant commerce/support history without leaving Tajeran.

## Audit Result
_Filled in by `/audit-feature customer-profile`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- Customer 360 view: Customer360Service.get_360() (services/customer_360.py:29-95) + GET /customers/{customer_id}/360 API (customers.py:110-125)
- Customer summary: conversation/ticket counts, channels, first/last seen, latest IDs (repositories/customers.py:61-126, schemas/customer_summary.py)
- Identity matching: CustomerIdentityService with normalization and conflict detection (services/customer_identity.py:36-100+), prevents unsafe merges
- Recent data aggregation: conversations, tickets, activity, workflow executions, tags all included in 360 response
- Tenant isolation: all queries scoped by user_id (services/customer_360.py, repositories/customers.py)
- Tests: test_customer_service_customer_360.py covers 360 bundle and user scoping
- Commerce order model: CommerceOrder with financial_status, fulfillment_status (services/support/commerce/commerce_order.py)

**Is it good enough?**
Partially. Strengths:
- Identity matching prevents customer merging errors
- Tenant isolation correct throughout
- Aggregates support history (conversations, tickets, activity, tags)
- Tests cover core functionality

Gaps vs spec:
- Orders, fulfillment, refunds, returns not in Customer360Read schema — spec requires "orders, order value, last order, fulfillment, refunds/returns"
- No commerce context exposed in 360 view (CommerceOrder model exists but not returned)
- Customer identity (email, phone) captured but not exposed in profile for display
- No sensitive data access controls documented (PII filtering for restricted roles)

**Gaps / risks:**
1. Commerce data missing from 360: spec requires orders/fulfillment/refunds/returns but Customer360Read only has support data (conversations/tickets/activity/tags)
2. No order value or last order timestamp: summary has conversation/ticket counts but no commerce KPIs
3. Commerce context service exists (customer_support_commerce_context.py) but not integrated into 360 view
4. Customer identity data not exposed in profile schema (phone/email available but not in API response for contact info)
5. No PII masking or sensitive data policy (full email/phone/customer names visible to all users with customer access)
6. No tests for commerce data aggregation or sensitive field filtering

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add commerce fields to Customer360Read schema: add orders: list[dict], last_order: dict | None, order_value: float, fulfillments: list[dict], refunds: list[dict], returns: list[dict] to schemas/customer_360.py
- [ ] Integrate commerce context in 360 service: call CustomerSupportCommerceContext in Customer360Service.get_360() to fetch orders/fulfillment/refund data and include in response dict
- [ ] Add customer contact info to profile: include phone and email from customer object in Customer360Read.customer and expose via API
- [ ] Add commerce repository: create repositories/commerce.py with methods list_customer_orders(), get_order_value(), list_customer_refunds(), list_customer_returns()
- [ ] Add PII protection middleware: create a utility function in services/ to mask email/phone for non-admin users, apply to customer profile responses
- [ ] Add tests for commerce aggregation: test_customer_service_customer_360_commerce.py covering orders, fulfillment status, refund/return history
- [ ] Add tests for sensitive field filtering: test_customer_service_customer_360_pii.py verifying email/phone masking for non-admin access
- [ ] Add Shopify order sync: create background job in services/ to periodically sync customer orders from Shopify and cache in customer profile 
