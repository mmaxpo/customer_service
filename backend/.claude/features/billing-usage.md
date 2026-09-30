# Feature: Billing & Usage

## Spec
- **What it should do:** Merchant can start a trial/subscription, see usage and billing status, upgrade/cancel, and Tajeran enforces the applicable limits.
- **Layer:** platform
- **Likely location (guess — verify, I don't have your repo):** app/platform/billing (plans, subscriptions, usage, limits)
- **Key entities:** Plan, Subscription, Trial, Usage Record, Usage Limit, Billing Customer, Invoice/Payment Status
- **Core rules to check against:** Billing belongs to workspace; usage attributed to the correct workspace; limits deterministic; billing state must not be inferred from frontend state; subscription changes auditable; product access must reflect actual billing state

## Acceptance criteria (from the v1 spec's "DONE" list)
- Trial, subscription state, plan storage, usage recording, limit enforcement all work
- Billing status visible; upgrade and cancel work
- Billing events idempotent; workspace isolation works
- Tests cover subscription/usage transitions

## Production success condition
> A real merchant can use Tajeran under a defined commercial plan, and Tajeran can accurately track usage and enforce the associated limits.

## Audit Result
_Filled in by `/audit-feature billing-usage`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- WorkspaceQuota model (app/tenancy/models.py) with monthly_token_limit, monthly_cost_microusd_limit, per_run_token_limit, per_run_llm_call_limit, per_run_tool_call_limit, concurrent_run_limit; created automatically on workspace creation
- WorkspaceUsageEvent model (app/tenancy/models.py) for tracking agent runs with status, model, tokens, calls, costs, timestamps
- WorkspaceUsageService (app/tenancy/usage.py) with begin_agent_run(), finish_agent_run(), resume_agent_run(), assert_run_access(), monthly_summary()
- Quota enforcement in begin_agent_run() blocking runs when limits exceeded; rejected runs logged with rejection_reason
- WorkspaceSubscription model (app/domains/customer_service/models/commercial.py) with plan, status, provider, entitlements, trial/period dates, cancel_at_period_end
- Plan definitions (app/domains/customer_service/services/billing_plans.py) for trial, starter, growth, pro with entitlements dict
- BillingWebhookService (app/domains/customer_service/services/billing.py) for processing external billing events with HMAC verification and idempotency
- Billing API endpoints (app/api/products/customer_service/commercial.py): GET /subscription, POST /billing/shopify/checkout, POST /billing/shopify/sync
- Tests verifying quota clamping and cost estimation (tests/tenancy/test_workspace_usage_quotas.py)

**Is it good enough?**
Partially. Core usage tracking and quota enforcement work well. However, billing and feature entitlement are incomplete:
- **Architectural issue**: WorkspaceSubscription lives in product layer, not platform. Billing should be cross-product.
- No trial auto-provisioning on signup — WorkspaceSubscription.plan defaults to "trial" but trial_ends_at is never set
- No subscription cancellation endpoint (can only be set via webhook)
- Entitlements stored but never enforced — e.g., monthly_conversations or members limits in plan entitlements are not checked anywhere
- No feature access gating based on subscription state (spec says "product access must reflect actual billing state") — can access features outside subscription
- No usage visibility endpoint for frontend to display current month usage/progress toward limits
- No subscription state transitions or soft failures when over-quota (only hard rejection on run start)
- No billing history or invoice/payment status tracking
- Webhook is source of truth but no protection against event loss/replay beyond 20-event dedup window
- No test for cross-workspace subscription isolation
- No test for feature access enforcement based on plan entitlements

**Gaps / risks:**
1. **Architectural**: WorkspaceSubscription belongs in platform, not product layer
2. Trial start date never set — WorkspaceSubscription.trial_ends_at can be null forever, confusing trial state
3. No cancel subscription endpoint — users can only cancel via external provider webhook
4. Entitlements enforced by frontend only, not backend — e.g., can add unlimited members regardless of plan.members limit
5. No GET /current/usage endpoint to surface usage for billing/tracking UI
6. No feature access gating — product behavior doesn't change based on subscription.plan or subscription.status
7. No billing history; can't show user invoices or payment history
8. Webhook handler doesn't validate workspace_id permissions (any webhook can update any workspace if they know the ID)
9. Per-run quota rejection happens at run start, no gradual throttling or warnings
10. No cost calculation for per-minute or overage charges — only fixed monthly limit

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] **CRITICAL**: Migrate WorkspaceSubscription model from app/domains/customer_service/models/commercial.py to app/platform (create app/platform/billing/models.py, move WorkspaceSubscription there, update imports)
- [ ] Create platform billing service (app/platform/billing/service.py) for subscription CRUD and state transitions
- [ ] Add auto-provision trial endpoint (POST /workspaces/{id}/start-trial) that sets trial_ends_at to +14 days and plan="trial"
- [ ] Add cancel subscription endpoint (POST /workspaces/{id}/cancel-subscription) that sets cancel_at_period_end=true or status="canceled"
- [ ] Add GET /workspaces/current/billing endpoint to return subscription plan, status, trial_ends_at, current_period_ends_at, entitlements
- [ ] Add entitlement enforcement: create app/platform/billing/enforcement.py with check_entitlement(workspace_id, feature) that blocks access based on subscription.plan
- [ ] Add member limit enforcement in workspace member add endpoint (app/api/workspaces.py): check against plan entitlements.members before adding
- [ ] Add monthly_conversations limit enforcement: add middleware or decorator in customer_service message creation to track monthly count and reject over limit
- [ ] Create billing history model (app/platform/billing/models.py) with workspace_id, event_type (charge, refund, trial_start, upgrade, downgrade), amount_microusd, timestamp
- [ ] Add test in tests/tenancy/test_billing_isolation.py for cross-workspace subscription isolation (user A workspace cannot see/modify user B workspace subscription) 
