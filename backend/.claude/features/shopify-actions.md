# Feature: Shopify Actions

## Spec
- **What it should do:** Execute a small, controlled set of Shopify write/destructive operations safely and verify their result.
- **Layer:** cross-layer (core capability dispatch → provider execution)
- **Likely location (guess — verify, I don't have your repo):** app/tcos capability resolver + providers/shopify/actions (add order note, cancel order, refund order)
- **Key entities:** Action (get_customer, get_order, get_product, get_fulfillment/tracking, add_order_note, cancel_order, refund_order), categories READ/WRITE/DESTRUCTIVE
- **Core rules to check against:** Actions tenant-scoped; AI cannot bypass authorization; destructive actions may require approval; actions auditable; idempotency considered; failed actions never reported as successful

## Acceptance criteria (from the v1 spec's "DONE" list)
- Read operations, add-order-note, cancel-order (under authorization), refund-order (under authorization) all work
- Risk levels exist; approval integration works
- Actions are audited and results verified
- Failed actions not falsely reported as successful
- Tests cover safe and failure paths

## Production success condition
> Tajeran can safely execute and verify authorized Shopify actions without bypassing tenant, permission, or approval controls.

## Audit Result
_Filled in by `/audit-feature shopify-actions`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- **Core execution layer** (`app/runtime/capabilities/execution/providers/shopify.py`): Two registered executors—`execute_shopify_get_order` (READ, wraps Shopify connection) and `execute_shopify_order_action` (delegates to business service).
- **Verification layer** (`app/runtime/capabilities/execution/verification/providers/shopify.py`): Two verifiers—`ShopifyRefundPreparationVerifier` (verifies refund prep only, not submission) and `ShopifyCancelOutcomeVerifier` (re-reads order to confirm cancel succeeded).
- **Workflow nodes** (`app/providers/shopify/runtime/nodes.py`): `ShopifyGetOrderNode` and `ShopifyOrderActionNode` for workflow integration. Actions passed through capability invoker.
- **Business service** (`app/domains/customer_service/services/shopify.py:perform_order_action`): Main execution point. Enforces approval gate for refund/reship (when `requires_durable_approval` flag set), idempotency via PostgreSQL advisory locks, order state validation (e.g., blocks cancel if `can_cancel=False`), and audit logging (for idempotent actions only).
- **Risk & approval** (`app/runtime/capabilities/registry/providers/shopify/manifest.py`): Marked as HIGH risk, requires approval. Supported actions: refund, cancel, update_shipping_address, reship, shipping_status.
- **Tests**: Idempotency tests (`test_customer_service_shopify_action_idempotency.py`), capability resolution tests (`test_shopify_order_action_semantic_capability.py`), action-type tests (change_address, reship coverage scattered across test files).

**Is it good enough?**
Mostly yes, but incomplete. Core safety (idempotency, approval, user-scoped access) is solid. **Three problems block v1 done:**
1. **Verification incomplete**: Only refund (preparation phase only) and cancel verified; reship, update_shipping_address, shipping_status have zero verification. If those actions fail silently in Shopify, the workflow reports success.
2. **Audit incomplete**: Audit logs only created when `idempotency_key` is provided (line 495-511 in shopify.py). Non-idempotent action paths produce zero audit trail. A malicious or buggy client calling without idempotency_key leaves no record.
3. **Test coverage gaps**: No tests for approval gate enforcement, no tests for non-idempotent paths, no tests for action failure/retry scenarios, no explicit tenant isolation tests (user_id isolation is implicit but never verified).

**Gaps / risks:**
- **Silent failures**: Reship, address change, shipping_status action execution has no post-execution verification. Provider error → success claim.
- **Audit trail gaps**: Only idempotent actions logged. Attackers or bugs using direct service calls bypass audit entirely.
- **Approval gate untested**: `_require_durable_approval` is called but no test confirms it actually blocks unauthorized execution.
- **Tenant boundary unclear**: Isolation relies on `get_active_connection(user_id)` lookup, but no test verifies a user from tenant A cannot execute actions on tenant B's orders through the capability layer.

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add comprehensive audit logging: in `app/domains/customer_service/services/shopify.py:perform_order_action`, move the audit log creation outside the `if idempotency_key:` block (lines 495-511) so all action executions are logged, whether or not idempotency_key is provided. Log action start, end, result, and any errors.
- [ ] Add verifiers for remaining actions: register verifiers in `app/runtime/capabilities/execution/verification/providers/shopify.py:register_shopify_task_verifiers()` for "shopify.order_action:reship", "shopify.order_action:change_address", and "shopify.order_action:shipping_status". Each should re-read order state or provider state to confirm the action outcome (similar to ShopifyCancelOutcomeVerifier pattern).
- [ ] Add test for non-idempotent action execution: in `tests/customer_service/shopify/`, create `test_customer_service_shopify_action_non_idempotent_execution.py` that calls `perform_order_action` without idempotency_key and verifies (1) action executes once, (2) result is returned, (3) audit log created.
- [ ] Add test for approval gate enforcement: in `tests/customer_service/shopify/test_customer_service_shopify_action_idempotency.py`, add a test that mocks `provider.requires_durable_approval=True`, calls perform_order_action with action="refund", and verifies `_require_durable_approval` is called (or add to a new test file). Also test that when approval is denied, the action does not execute.
- [ ] Add test for action failure scenarios: in the same test file, test that when `provider.refund_order()` raises an exception, the method propagates it correctly, audit is logged with error state, and second call with same idempotency key returns the error (not re-tries).
- [ ] Add explicit tenant isolation test: in `tests/runtime/contracts/`, create `test_shopify_actions_tenant_isolation.py` with a test that creates two users (simulating two tenants), calls `execute_shopify_order_action` with user A's context, and verifies it cannot access user B's Shopify connection or orders. 
