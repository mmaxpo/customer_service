# Feature: AI Actions

## Spec
- **What it should do:** Execute controlled customer-service operations end-to-end (e.g. order status lookup, refund with approval) and verify their outcomes.
- **Layer:** cross-layer (core capability dispatch → provider/product execution)
- **Likely location (guess — verify, I don't have your repo):** app/tcos capability resolver (order status, refund, cancellation end-to-end flows)
- **Key entities:** Action Request, Capability, Action Execution, Approval, Verification, Action Result, Outcome
- **Core rules to check against:** Every action has an explicit capability; input validated; authorization checked; risk known; destructive actions require configured authorization; verification required where possible; failure not represented as success

## Acceptance criteria (from the v1 spec's "DONE" list)
- v1 supported action scenarios (order lookup, tracking, order note, refund, cancellation) work end-to-end
- Authorization, approval, verification all work
- Outcomes recorded; failures recoverable/escalatable
- Tests cover complete customer scenarios

## Production success condition
> Tajeran can complete a real customer-service task from customer request through verified business outcome.

## Audit Result
_Filled in by `/audit-feature ai-actions`. Re-run to refresh; each run overwrites this section only._

**Status:** in-progress — see PROGRESS TRACKER below

**What exists today:**
- **Capability system** (core layer: `app/runtime/capabilities/`): Semantic capability resolver, executor registry, outcome reporting. Capabilities defined with risk levels (SAFE, MEDIUM, HIGH), approval requirements, required/optional inputs. CapabilityInvoker orchestrates resolution → execution → verification → outcome reporting.
- **Shopify ecommerce capabilities** (core registry + provider): Two capabilities registered via `app/runtime/capabilities/registry/providers/shopify/manifest.py`: (1) `ecommerce.orders.get` (SAFE, no approval), (2) `ecommerce.orders.action` (HIGH risk, requires approval). Supported actions: refund, cancel, update_shipping_address, reship, shipping_status.
- **Action execution** (core: `app/runtime/capabilities/execution/providers/shopify.py`): Two executors—`execute_shopify_get_order` and `execute_shopify_order_action`—delegate to `ShopifyRuntimeService` which is tenant/user-scoped via `get_active_connection(user_id)`.
- **Action verification** (core: `app/runtime/capabilities/execution/verification/providers/shopify.py`): Verifiers for refund (preparation only) and cancel (re-read order state). Verification outcomes: VERIFIED, PARTIALLY_VERIFIED, INCONCLUSIVE, FAILED, NOT_VERIFIABLE.
- **Suggested actions** (product layer: `app/domains/customer_service/services/suggested_actions.py`): Generate & execute order-related actions (assign, escalate, refund, cancel, address_change, damaged_item). Execute endpoint (line 891+) handles escalate/assign/refund. Refund execution requires Shopify integration (returns 501 if missing).
- **Idempotency & approval** (cross-layer): Idempotency keys via PostgreSQL advisory locks (seen in Shopify actions audit). Approval gate via `_require_durable_approval` for refund/reship when flag set. Audit logging for idempotent actions.
- **Tests**: End-to-end tests (test_complex_support_intake_e2e.py) verify order lookup + action workflow with Shopify provider mocking. Suggested action tests cover generate, accept, execute lifecycle. Capability resolution tests verify binding selection and risk classification.

**Is it good enough?**
Partially. Core infrastructure is solid, but **feature is incomplete for production v1**. **Three significant gaps:**
1. **Incomplete action coverage**: v1 spec requires (order lookup, tracking, order note, refund, cancellation). Implemented: lookup (get_order) and cancellation (cancel action). Missing or untested: order tracking (no capability), add order note (capability exists but execution path unclear), reship (capability exists, provider implemented, but no end-to-end test showing full workflow).
2. **Verification incomplete**: Only refund (preparation) and cancel verified. Address change, reship, tracking have no verification. If these fail in provider, workflow claims success without proof.
3. **No structured outcome recording**: Actions store results in SuggestedAction.payload, but there's no durable Action Execution record tying together request → authorization → execution → verification → business outcome. Failures are not clearly marked as "recoverable" vs "escalatable." No audit trail for non-idempotent actions.

**Gaps / risks:**
- **Silent failures**: Reship and address-change actions execute but have zero verification. Provider errors → workflow proceeds as if succeeded.
- **Outcome traceability**: When an action completes, there's no canonical record of what was requested, who approved it, what was executed, verification outcome, and remediation options if it failed.
- **Tracking capability missing**: No capability for "get_order_tracking" or similar. If customer asks "where's my order?", there's no AI-driven action to answer that via provider.
- **Add-note action unclear**: Spec mentions "order note" but suggested_actions.py doesn't explicitly handle it as action_type. (May be implicit in Shopify order_action:note, but not tested end-to-end.)
- **No fallback on partial verification**: If refund verification is PARTIALLY_VERIFIED (prep succeeded, but submission status unknown), workflow doesn't escalate or retry verification.
- **Error recovery path missing**: When an action fails, there's no "what now?" path. No test covers: action failed → should we retry, escalate, or offer customer alternative.

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add order tracking capability: in `app/runtime/capabilities/registry/providers/shopify/manifest.py`, register a new capability `ecommerce.orders.tracking` (SAFE, no approval) with binding to Shopify provider. Implement `execute_shopify_get_tracking` in `app/runtime/capabilities/execution/providers/shopify.py` that calls `shopify.get_order_tracking(user_id, order_ref)`. Add executor registration.
- [ ] Implement add-order-note capability: add capability `ecommerce.orders.add_note` (MEDIUM risk, optional approval) to manifest with binding to `shopify.add_order_note`. Implement executor in execution/providers/shopify.py that calls `shopify.add_order_note(user_id, order_ref, note)`. Test end-to-end in suggested_actions workflow.
- [ ] Add verifiers for remaining actions: in `app/runtime/capabilities/execution/verification/providers/shopify.py`, implement `ShopifyAddressChangeVerifier` (re-read order shipping_address), `ShopifyRepairVerifier` (re-read order line_items for damage flag), and `ShopifyTrackingVerifier` (re-read tracking info). Register all three in `register_shopify_task_verifiers()`.
- [ ] Create Action Execution record model: in `app/domains/customer_service/models/commercial.py`, add `ActionExecution` table with fields: id (UUID), user_id, conversation_id, capability_id, provider_id, action_type, request_payload (jsonb), authorization_status (approved/denied/pending), approval_user_id, execution_status (pending/completed/failed), execution_output (jsonb), verification_outcome (verified/inconclusive/failed), business_outcome (text), error_detail (text), created_at, updated_at. Add foreign key from Conversation or Ticket.
- [ ] Wire action execution results to ActionExecution record: modify `app/runtime/capabilities/execution/runtime.py` or outcome reporting layer to persist CapabilityExecutionOutcome to ActionExecution table after verification completes. Include verification_outcome and business_outcome assessment.
- [ ] Add error recovery logic: in suggested_actions.py:execute_action, when action result is FAILED or INCONCLUSIVE, call a new `_assess_recovery_action()` that returns {can_retry: bool, should_escalate: bool, customer_message: str}. For refund verification INCONCLUSIVE, set should_escalate=True and generate escalation reason.
- [ ] Add end-to-end test for full action lifecycle: in `tests/customer_service/shopify/test_customer_service_shopify_action_e2e.py`, create test that (1) customer request with specific order issue, (2) AI suggests correct action, (3) action is approved, (4) action executes end-to-end, (5) verification confirms outcome, (6) ActionExecution record is created with full lineage, (7) business outcome is recorded and customer is notified.
- [ ] Add failure recovery test: in same test file, create test that (1) action execution fails in provider, (2) verification is INCONCLUSIVE, (3) ActionExecution.verification_outcome is INCONCLUSIVE, (4) _assess_recovery_action recommends escalation, (5) human is notified and can manually intervene. 


---

# ai-actions verification round 1
_generated 2026-09-21T18:46:53_

## A. Shopify capability manifest — exact registered capabilities

=== app/runtime/capabilities/registry/providers/shopify/manifest.py (157 lines) ===
   1: from __future__ import annotations
   2: 
   3: from app.runtime.capabilities.registry.registries import BindingRegistry
   4: from app.runtime.capabilities.registry.registries import CapabilityRegistry
   5: from app.runtime.capabilities.registry.registries import CapabilityAliasRegistry
   6: from app.runtime.capabilities.registry.registries import ProviderRegistry
   7: from app.runtime.capabilities.registry.contracts import (
   8:     CapabilityCategory,
   9:     CapabilityDefinition,
  10:     CapabilityDomain,
  11:     CapabilityProvider,
  12:     CapabilityProviderKind,
  13:     CapabilityRisk,
  14:     ProviderBinding,
  15: )
  16: 
  17: 
  18: def register_manifest(
  19:     *,
  20:     capabilities: CapabilityRegistry,
  21:     providers: ProviderRegistry,
  22:     bindings: BindingRegistry,
  23:     aliases: CapabilityAliasRegistry,
  24: ) -> None:
  25:     capabilities.register_domain(
  26:         CapabilityDomain(
  27:             id="ecommerce",
  28:             title="Ecommerce",
  29:             description="Commerce capabilities for orders, refunds, fulfillment, and products.",
  30:         )
  31:     )
  32: 
  33:     capabilities.register_category(
  34:         CapabilityCategory(
  35:             id="ecommerce.orders",
  36:             domain_id="ecommerce",
  37:             title="Orders",
  38:             description="Order lookup and order status capabilities.",
  39:         )
  40:     )
  41: 
  42:     capabilities.register_capability(
  43:         CapabilityDefinition(
  44:             id="ecommerce.orders.get",
  45:             category_id="ecommerce.orders",
  46:             title="Get Order",
  47:             description="Retrieve an ecommerce order by reference.",
  48:             semantic_key="order.lookup",
  49:             required_inputs=("order_ref",),
  50:             output_key="shopify_order",
  51:             risk=CapabilityRisk.SAFE,
  52:             tags=("ecommerce", "orders", "lookup", "shopify"),
  53:             metadata={"legacy_ids": ("shopify.get_order",)},
  54:         )
  55:     )
  56: 
  57:     capabilities.register_capability(
  58:         CapabilityDefinition(
  59:             id="ecommerce.orders.action",
  60:             category_id="ecommerce.orders",
  61:             title="Perform Order Action",
  62:             description=(
  63:                 "Perform a guarded ecommerce order action such as refund, "
  64:                 "cancel, address update, reship, or shipping-status lookup."
  65:             ),
  66:             semantic_key="order.action",
  67:             required_inputs=("action", "order_ref"),
  68:             optional_inputs=(
  69:                 "reason",
  70:                 "note",
  71:                 "new_address",
  72:                 "amount",
  73:                 "scope",
  74:                 "idempotency_key",
  75:             ),
  76:             output_key="shopify_order_action",
  77:             risk=CapabilityRisk.HIGH,
  78:             tags=("ecommerce", "orders", "action", "shopify"),
  79:             metadata={
  80:                 "legacy_ids": ("shopify.order_action",),
  81:                 "supported_actions": (
  82:                     "refund",
  83:                     "cancel",
  84:                     "update_shipping_address",
  85:                     "reship",
  86:                     "shipping_status",
  87:                 ),
  88:             },
  89:         )
  90:     )
  91: 
  92:     providers.register(
  93:         CapabilityProvider(
  94:             id="shopify",
  95:             title="Shopify",
  96:             kind=CapabilityProviderKind.BUILTIN,
  97:             description="Shopify ecommerce provider.",
  98:             requires_auth=True,
  99:             supports_fallback=True,
 100:             metadata={"integration": "shopify"},
 101:         )
 102:     )
 103: 
 104:     bindings.register(
 105:         ProviderBinding(
 106:             capability_id="ecommerce.orders.get",
 107:             provider_id="shopify",
 108:             provider_ref="shopify.get_order",
 109:             runtime_node_type="capability.invoke",
 110:             required_inputs=("order_ref",),
 111:             output_key="shopify_order",
 112:             priority=100,
 113:             enabled=True,
 114:             risk=CapabilityRisk.SAFE,
 115:             requires_approval=False,
 116:             metadata={"legacy_capability_id": "shopify.get_order"},
 117:         )
 118:     )
 119: 
 120:     bindings.register(
 121:         ProviderBinding(
 122:             capability_id="ecommerce.orders.action",
 123:             provider_id="shopify",
 124:             provider_ref="shopify.order_action",
 125:             runtime_node_type="capability.invoke",
 126:             required_inputs=("action", "order_ref"),
 127:             optional_inputs=(
 128:                 "reason",
 129:                 "note",
 130:                 "new_address",
 131:                 "amount",
 132:                 "scope",
 133:                 "idempotency_key",
 134:             ),
 135:             output_key="shopify_order_action",
 136:             priority=100,
 137:             enabled=True,
 138:             risk=CapabilityRisk.HIGH,
 139:             requires_approval=True,
 140:             metadata={
 141:                 "legacy_capability_id": "shopify.order_action",
 142:                 "supported_actions": (
 143:                     "refund",
 144:                     "cancel",
 145:                     "update_shipping_address",
 146:                     "reship",
 147:                     "shipping_status",
 148:                 ),
 149:             },
 150:         )
 151:     )
 152: 
 153:     aliases.register("shopify.get_order", "ecommerce.orders.get")
 154:     aliases.register(
 155:         "shopify.order_action",
 156:         "ecommerce.orders.action",
 157:     )

## B. Shopify execution providers — exact executors present

=== app/runtime/capabilities/execution/providers/shopify.py (145 lines) ===
   1: from __future__ import annotations
   2: 
   3: from typing import Any
   4: 
   5: from fastapi import HTTPException
   6: 
   7: from app.runtime.capabilities.execution.contracts import (
   8:     CapabilityExecutionContext,
   9: )
  10: from app.runtime.capabilities.execution.registry import (
  11:     CapabilityExecutorRegistry,
  12: )
  13: 
  14: 
  15: def _require_shopify_service(
  16:     context: CapabilityExecutionContext,
  17: ) -> Any:
  18:     shopify = getattr(
  19:         getattr(context.services, "business", None),
  20:         "shopify",
  21:         None,
  22:     )
  23: 
  24:     if shopify is None:
  25:         raise ValueError(
  26:             f"Capability {context.invocation.capability_id} "
  27:             "requires services.business.shopify"
  28:         )
  29: 
  30:     return shopify
  31: 
  32: 
  33: def _resolve_user_id(
  34:     context: CapabilityExecutionContext,
  35: ) -> Any:
  36:     user_id = (
  37:         context.invocation.user_id
  38:         or getattr(
  39:             getattr(context.services, "identity", None),
  40:             "user_id",
  41:             None,
  42:         )
  43:     )
  44: 
  45:     if user_id is None:
  46:         raise ValueError(
  47:             f"Capability {context.invocation.capability_id} requires user_id"
  48:         )
  49: 
  50:     return user_id
  51: 
  52: 
  53: async def execute_shopify_get_order(
  54:     context: CapabilityExecutionContext,
  55: ) -> Any:
  56:     shopify = _require_shopify_service(context)
  57:     user_id = _resolve_user_id(context)
  58: 
  59:     order_ref = str(
  60:         context.invocation.inputs.get("order_ref") or ""
  61:     ).strip()
  62: 
  63:     if not order_ref:
  64:         raise ValueError(
  65:             f"Capability {context.invocation.capability_id} "
  66:             "requires payload.order_ref"
  67:         )
  68: 
  69:     try:
  70:         return await shopify.get_order(
  71:             user_id=user_id,
  72:             order_ref=order_ref,
  73:         )
  74:     except HTTPException as exc:
  75:         detail = str(exc.detail or "").strip()
  76: 
  77:         if not (
  78:             exc.status_code == 404
  79:             and "order" in detail.lower()
  80:         ):
  81:             raise
  82: 
  83:         customer_safe_message = (
  84:             f"I couldn't find order {order_ref}. "
  85:             "Please check the order number and try again."
  86:         )
  87: 
  88:         # Order-not-found is a normal business result. It must not cause the
  89:         # workflow job to retry or enter dead-letter.
  90:         return {
  91:             "found": False,
  92:             "order_ref": order_ref,
  93:             "order_id": None,
  94:             "order_name": None,
  95:             "customer_email": None,
  96:             "payload": None,
  97:             "context": None,
  98:             "summary": {
  99:                 "found": False,
 100:                 "order_ref": order_ref,
 101:                 "order_name": order_ref,
 102:                 "customer_safe_note": customer_safe_message,
 103:                 "available_actions": {},
 104:             },
 105:         }
 106: 
 107: 
 108: async def execute_shopify_order_action(
 109:     context: CapabilityExecutionContext,
 110: ) -> Any:
 111:     shopify = _require_shopify_service(context)
 112:     user_id = _resolve_user_id(context)
 113:     payload = context.invocation.inputs
 114: 
 115:     return await shopify.perform_order_action(
 116:         user_id=user_id,
 117:         action=payload["action"],
 118:         order_ref=payload["order_ref"],
 119:         reason=payload.get("reason"),
 120:         note=payload.get("note"),
 121:         new_address=payload.get("new_address"),
 122:         amount=payload.get("amount"),
 123:         scope=payload.get("scope"),
 124:         idempotency_key=payload.get("idempotency_key"),
 125:     )
 126: 
 127: 
 128: def register_shopify_executors(
 129:     registry: CapabilityExecutorRegistry,
 130: ) -> None:
 131:     registry.register(
 132:         "shopify.get_order",
 133:         execute_shopify_get_order,
 134:     )
 135:     registry.register(
 136:         "shopify.order_action",
 137:         execute_shopify_order_action,
 138:     )
 139: 
 140: 
 141: __all__ = [
 142:     "execute_shopify_get_order",
 143:     "execute_shopify_order_action",
 144:     "register_shopify_executors",
 145: ]

## C. Shopify verification providers — exact verifiers present

=== app/runtime/capabilities/execution/verification/providers/shopify.py (430 lines) ===
   1: from __future__ import annotations
   2: 
   3: from typing import Any
   4: 
   5: from app.runtime.capabilities.execution.verification.contracts import (
   6:     TaskVerificationContext,
   7:     TaskVerificationEvidence,
   8:     TaskVerificationMethod,
   9:     TaskVerificationOutcome,
  10:     TaskVerificationResult,
  11: )
  12: from app.runtime.capabilities.execution.verification.registry import (
  13:     TaskVerifierRegistry,
  14: )
  15: 
  16: 
  17: class ShopifyRefundPreparationVerifier:
  18:     """
  19:     Verify only refund preparation.
  20: 
  21:     The current real Shopify provider does not submit money-moving refunds.
  22:     Therefore this verifier must never claim that the customer was refunded.
  23:     """
  24: 
  25:     async def verify(
  26:         self,
  27:         context: TaskVerificationContext,
  28:     ) -> TaskVerificationResult:
  29:         request = context.request
  30:         output = (
  31:             request.execution_output
  32:             if isinstance(
  33:                 request.execution_output,
  34:                 dict,
  35:             )
  36:             else {}
  37:         )
  38:         payload = output.get("payload")
  39: 
  40:         if not isinstance(payload, dict):
  41:             payload = output
  42: 
  43:         status = str(
  44:             payload.get("status")
  45:             or output.get("status")
  46:             or ""
  47:         ).strip().lower()
  48: 
  49:         evidence = TaskVerificationEvidence(
  50:             kind="refund_preparation",
  51:             source="capability_execution",
  52:             data={
  53:                 "status": status or None,
  54:                 "order_id": (
  55:                     payload.get("order_id")
  56:                     or output.get("order_id")
  57:                 ),
  58:                 "order_name": (
  59:                     payload.get("order_name")
  60:                     or output.get("order_name")
  61:                 ),
  62:                 "requested_amount": (
  63:                     request.inputs.get("amount")
  64:                 ),
  65:                 "prepared_amount": (
  66:                     payload.get("amount")
  67:                 ),
  68:             },
  69:         )
  70: 
  71:         if status == "prepared":
  72:             return _result(
  73:                 context=context,
  74:                 outcome=(
  75:                     TaskVerificationOutcome
  76:                     .PARTIALLY_VERIFIED
  77:                 ),
  78:                 method=(
  79:                     TaskVerificationMethod
  80:                     .EXECUTION_EVIDENCE
  81:                 ),
  82:                 reason_code=(
  83:                     "refund_prepared_not_submitted"
  84:                 ),
  85:                 summary=(
  86:                     "Refund preparation was confirmed, "
  87:                     "but no Shopify refund was submitted."
  88:                 ),
  89:                 confidence=1.0,
  90:                 retryable=False,
  91:                 observed_outcome={
  92:                     "refund_prepared": True,
  93:                     "refund_submitted": False,
  94:                     "refund_completed": False,
  95:                 },
  96:                 evidence=[evidence],
  97:             )
  98: 
  99:         if status == "blocked":
 100:             return _result(
 101:                 context=context,
 102:                 outcome=(
 103:                     TaskVerificationOutcome.FAILED
 104:                 ),
 105:                 method=(
 106:                     TaskVerificationMethod
 107:                     .EXECUTION_EVIDENCE
 108:                 ),
 109:                 reason_code=(
 110:                     "refund_preparation_blocked"
 111:                 ),
 112:                 summary=(
 113:                     "The refund was not prepared "
 114:                     "because the action was blocked."
 115:                 ),
 116:                 confidence=1.0,
 117:                 retryable=False,
 118:                 observed_outcome={
 119:                     "refund_prepared": False,
 120:                     "refund_submitted": False,
 121:                     "refund_completed": False,
 122:                 },
 123:                 evidence=[evidence],
 124:             )
 125: 
 126:         return _result(
 127:             context=context,
 128:             outcome=(
 129:                 TaskVerificationOutcome
 130:                 .INCONCLUSIVE
 131:             ),
 132:             method=(
 133:                 TaskVerificationMethod
 134:                 .EXECUTION_EVIDENCE
 135:             ),
 136:             reason_code=(
 137:                 "refund_preparation_status_unknown"
 138:             ),
 139:             summary=(
 140:                 "The execution response does not "
 141:                 "prove refund preparation."
 142:             ),
 143:             confidence=0.0,
 144:             retryable=False,
 145:             observed_outcome={
 146:                 "refund_prepared": None,
 147:                 "refund_submitted": None,
 148:                 "refund_completed": None,
 149:             },
 150:             evidence=[evidence],
 151:         )
 152: 
 153: 
 154: class ShopifyCancelOutcomeVerifier:
 155:     """
 156:     Verify cancellation by reading fresh Shopify order state.
 157: 
 158:     The original cancellation response is not treated as proof. A successful
 159:     result requires the newly observed Shopify order to contain cancelled_at.
 160:     """
 161: 
 162:     async def verify(
 163:         self,
 164:         context: TaskVerificationContext,
 165:     ) -> TaskVerificationResult:
 166:         request = context.request
 167: 
 168:         order_ref = str(
 169:             request.inputs.get("order_ref")
 170:             or ""
 171:         ).strip()
 172: 
 173:         if not order_ref:
 174:             return _result(
 175:                 context=context,
 176:                 outcome=(
 177:                     TaskVerificationOutcome
 178:                     .NOT_VERIFIABLE
 179:                 ),
 180:                 method=(
 181:                     TaskVerificationMethod
 182:                     .REMOTE_STATE
 183:                 ),
 184:                 reason_code=(
 185:                     "cancel_order_ref_missing"
 186:                 ),
 187:                 summary=(
 188:                     "Cancellation cannot be verified "
 189:                     "without an order reference."
 190:                 ),
 191:                 confidence=1.0,
 192:                 retryable=False,
 193:             )
 194: 
 195:         shopify = _require_shopify_service(
 196:             context
 197:         )
 198: 
 199:         try:
 200:             order = await (
 201:                 shopify.get_order_fresh(
 202:                     user_id=request.user_id,
 203:                     order_ref=order_ref,
 204:                 )
 205:             )
 206:         except Exception as exc:
 207:             return _result(
 208:                 context=context,
 209:                 outcome=(
 210:                     TaskVerificationOutcome
 211:                     .INCONCLUSIVE
 212:                 ),
 213:                 method=(
 214:                     TaskVerificationMethod
 215:                     .REMOTE_STATE
 216:                 ),
 217:                 reason_code=(
 218:                     "cancel_remote_observation_failed"
 219:                 ),
 220:                 summary=(
 221:                     "Fresh Shopify order state could "
 222:                     "not be retrieved."
 223:                 ),
 224:                 confidence=0.0,
 225:                 retryable=True,
 226:                 evidence=[
 227:                     TaskVerificationEvidence(
 228:                         kind=(
 229:                             "remote_observation_error"
 230:                         ),
 231:                         source="shopify",
 232:                         data={
 233:                             "order_ref": order_ref,
 234:                             "exception_type": (
 235:                                 type(exc).__name__
 236:                             ),
 237:                         },
 238:                     )
 239:                 ],
 240:             )
 241: 
 242:         if not isinstance(order, dict):
 243:             return _result(
 244:                 context=context,
 245:                 outcome=(
 246:                     TaskVerificationOutcome
 247:                     .INCONCLUSIVE
 248:                 ),
 249:                 method=(
 250:                     TaskVerificationMethod
 251:                     .REMOTE_STATE
 252:                 ),
 253:                 reason_code=(
 254:                     "cancel_order_not_observed"
 255:                 ),
 256:                 summary=(
 257:                     "Shopify did not return an order "
 258:                     "for cancellation verification."
 259:                 ),
 260:                 confidence=0.0,
 261:                 retryable=True,
 262:             )
 263: 
 264:         cancelled_at = order.get(
 265:             "cancelled_at"
 266:         )
 267: 
 268:         evidence = TaskVerificationEvidence(
 269:             kind="shopify_order_state",
 270:             source="shopify",
 271:             data={
 272:                 "order_id": order.get("id"),
 273:                 "order_name": order.get("name"),
 274:                 "cancelled_at": cancelled_at,
 275:                 "financial_status": order.get(
 276:                     "financial_status"
 277:                 ),
 278:                 "fulfillment_status": order.get(
 279:                     "fulfillment_status"
 280:                 ),
 281:             },
 282:         )
 283: 
 284:         if cancelled_at:
 285:             return _result(
 286:                 context=context,
 287:                 outcome=(
 288:                     TaskVerificationOutcome
 289:                     .VERIFIED
 290:                 ),
 291:                 method=(
 292:                     TaskVerificationMethod
 293:                     .REMOTE_STATE
 294:                 ),
 295:                 reason_code=(
 296:                     "shopify_order_cancelled"
 297:                 ),
 298:                 summary=(
 299:                     "Fresh Shopify state confirms "
 300:                     "that the order is cancelled."
 301:                 ),
 302:                 confidence=1.0,
 303:                 retryable=False,
 304:                 observed_outcome={
 305:                     "order_cancelled": True,
 306:                     "cancelled_at": cancelled_at,
 307:                 },
 308:                 evidence=[evidence],
 309:             )
 310: 
 311:         return _result(
 312:             context=context,
 313:             outcome=(
 314:                 TaskVerificationOutcome.FAILED
 315:             ),
 316:             method=(
 317:                 TaskVerificationMethod
 318:                 .REMOTE_STATE
 319:             ),
 320:             reason_code=(
 321:                 "shopify_order_not_cancelled"
 322:             ),
 323:             summary=(
 324:                 "Fresh Shopify state shows that "
 325:                 "the order is not cancelled."
 326:             ),
 327:             confidence=1.0,
 328:             retryable=False,
 329:             observed_outcome={
 330:                 "order_cancelled": False,
 331:                 "cancelled_at": None,
 332:             },
 333:             evidence=[evidence],
 334:         )
 335: 
 336: 
 337: def register_shopify_task_verifiers(
 338:     registry: TaskVerifierRegistry,
 339: ) -> None:
 340:     registry.register(
 341:         "shopify.order_action:refund",
 342:         ShopifyRefundPreparationVerifier(),
 343:     )
 344:     registry.register(
 345:         "shopify.order_action:cancel",
 346:         ShopifyCancelOutcomeVerifier(),
 347:     )
 348: 
 349: 
 350: def _require_shopify_service(
 351:     context: TaskVerificationContext,
 352: ) -> Any:
 353:     services = context.services
 354: 
 355:     shopify = getattr(
 356:         getattr(
 357:             services,
 358:             "business",
 359:             None,
 360:         ),
 361:         "shopify",
 362:         None,
 363:     )
 364: 
 365:     if shopify is None:
 366:         shopify = getattr(
 367:             services,
 368:             "shopify",
 369:             None,
 370:         )
 371: 
 372:     if shopify is None:
 373:         raise ValueError(
 374:             "Shopify task verification requires "
 375:             "a Shopify business service"
 376:         )
 377: 
 378:     return shopify
 379: 
 380: 
 381: def _result(
 382:     *,
 383:     context: TaskVerificationContext,
 384:     outcome: TaskVerificationOutcome,
 385:     method: TaskVerificationMethod,
 386:     reason_code: str,
 387:     summary: str,
 388:     confidence: float,
 389:     retryable: bool,
 390:     observed_outcome: (
 391:         dict[str, Any] | None
 392:     ) = None,
 393:     evidence: (
 394:         list[TaskVerificationEvidence]
 395:         | None
 396:     ) = None,
 397: ) -> TaskVerificationResult:
 398:     request = context.request
 399: 
 400:     return TaskVerificationResult(
  ... (30 more lines truncated)

## D. Does an outcome/execution record model ALREADY exist? (checking claimed-missing ActionExecution)

--- searching for: ActionExecution (claimed to not exist) ---

--- searching for: CustomerSupportOutcome* (seen earlier in models list) ---
  app/domains/customer_service/models/__init__.py  (matched 'CustomerSupportOutcomeRecord')
  app/domains/customer_service/models/models.py  (matched 'CustomerSupportOutcomeRecord')
  app/domains/customer_service/models/outcomes.py  (matched 'CustomerSupportOutcomeRecord')
  app/domains/customer_service/repositories/customer_support_outcomes.py  (matched 'CustomerSupportOutcomeRecord')
  app/domains/customer_service/runtime/nodes/customer_support_outcome_recording.py  (matched 'CustomerSupportOutcomeRecord')
  app/domains/customer_service/runtime/nodes/registration.py  (matched 'CustomerSupportOutcomeRecord')
  app/domains/customer_service/services/support/outcome/customer_support_outcome_evaluation.py  (matched 'CustomerSupportOutcomeRecord')
  app/domains/customer_service/services/support/outcome/customer_support_outcome_recording.py  (matched 'CustomerSupportOutcomeRecord')
  app/domains/customer_service/services/support/planning/customer_support_review_plan_loader.py  (matched 'CustomerSupportOutcomeRecord')
  app/domains/customer_service/models/outcomes.py  (matched 'class CustomerSupportOutcome')
  app/domains/customer_service/repositories/customer_support_outcome_evaluations.py  (matched 'class CustomerSupportOutcome')
  app/domains/customer_service/repositories/customer_support_outcomes.py  (matched 'class CustomerSupportOutcome')
  app/domains/customer_service/runtime/nodes/customer_support_outcome.py  (matched 'class CustomerSupportOutcome')
  app/domains/customer_service/runtime/nodes/customer_support_outcome_recording.py  (matched 'class CustomerSupportOutcome')
  app/domains/customer_service/services/support/outcome/customer_support_outcome.py  (matched 'class CustomerSupportOutcome')
  app/domains/customer_service/services/support/outcome/customer_support_outcome_evaluation.py  (matched 'class CustomerSupportOutcome')
  app/domains/customer_service/services/support/outcome/customer_support_outcome_evaluation_service.py  (matched 'class CustomerSupportOutcome')
  app/domains/customer_service/services/support/outcome/customer_support_outcome_recording.py  (matched 'class CustomerSupportOutcome')

--- searching for: outcome evaluation records ---
  app/domains/customer_service/models/outcomes.py  (matched 'outcome_evaluations')
  app/domains/customer_service/services/support/learning/customer_support_business_learning_projection.py  (matched 'outcome_evaluations')
  app/domains/customer_service/services/support/learning/customer_support_objective_learning_source_loader.py  (matched 'outcome_evaluations')
  app/domains/customer_service/services/support/outcome/customer_support_outcome_evaluation_service.py  (matched 'outcome_evaluations')
  app/domains/customer_service/services/support/resolution/customer_support_resolution_projection.py  (matched 'outcome_evaluations')
  app/domains/customer_service/models/__init__.py  (matched 'CustomerSupportOutcomeEvaluationRecord')
  app/domains/customer_service/models/models.py  (matched 'CustomerSupportOutcomeEvaluationRecord')
  app/domains/customer_service/models/outcomes.py  (matched 'CustomerSupportOutcomeEvaluationRecord')
  app/domains/customer_service/repositories/customer_support_outcome_evaluations.py  (matched 'CustomerSupportOutcomeEvaluationRecord')
  app/domains/customer_service/services/support/outcome/customer_support_outcome_evaluation_service.py  (matched 'CustomerSupportOutcomeEvaluationRecord')

## E. tracking / add_note capability search (claimed missing)

  'get_order_tracking': NO MATCHES

  'add_order_note': NO MATCHES

  'orders.tracking': NO MATCHES

  'orders.add_note': NO MATCHES

  'order_note': NO MATCHES

---

# ai-actions verification round 2: does CustomerSupportOutcomeRecord already cover ActionExecution's job?
_generated 2026-09-21T18:47:34_

## A. outcomes.py — full model definitions

=== app/domains/customer_service/models/outcomes.py (259 lines) ===
   1: from __future__ import annotations
   2: 
   3: import uuid
   4: from datetime import datetime
   5: 
   6: from sqlalchemy import (
   7:     DateTime,
   8:     Float,
   9:     ForeignKey,
  10:     Index,
  11:     Integer,
  12:     String,
  13:     Text,
  14:     UniqueConstraint,
  15:     func,
  16: )
  17: from sqlalchemy.dialects.postgresql import JSONB, UUID
  18: from sqlalchemy.orm import Mapped, mapped_column
  19: 
  20: from app.models.models import Base
  21: 
  22: 
  23: class CustomerSupportOutcomeRecord(Base):
  24:     """Canonical immutable business outcome for one support review plan."""
  25: 
  26:     __tablename__ = "cs_support_outcomes"
  27:     __table_args__ = (
  28:         UniqueConstraint(
  29:             "user_id",
  30:             "review_plan_id",
  31:             name="uq_cs_support_outcomes_user_review_plan",
  32:         ),
  33:         Index(
  34:             "ix_cs_support_outcomes_user_created",
  35:             "user_id",
  36:             "created_at",
  37:         ),
  38:         Index(
  39:             "ix_cs_support_outcomes_user_conversation_created",
  40:             "user_id",
  41:             "conversation_id",
  42:             "created_at",
  43:         ),
  44:     )
  45: 
  46:     id: Mapped[uuid.UUID] = mapped_column(
  47:         UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
  48:     )
  49:     user_id: Mapped[uuid.UUID] = mapped_column(
  50:         UUID(as_uuid=True), nullable=False, index=True
  51:     )
  52:     review_plan_id: Mapped[str] = mapped_column(
  53:         String(128), nullable=False
  54:     )
  55:     workflow_run_id: Mapped[uuid.UUID] = mapped_column(
  56:         UUID(as_uuid=True), nullable=False, index=True
  57:     )
  58:     chat_session_id: Mapped[uuid.UUID] = mapped_column(
  59:         UUID(as_uuid=True), nullable=False, index=True
  60:     )
  61:     conversation_id: Mapped[uuid.UUID] = mapped_column(
  62:         UUID(as_uuid=True), nullable=False, index=True
  63:     )
  64: 
  65:     objective_namespace: Mapped[str] = mapped_column(
  66:         String(100), nullable=False, default="customer_service.support"
  67:     )
  68:     objective_ref: Mapped[str] = mapped_column(
  69:         String(128), nullable=False, index=True
  70:     )
  71:     source_objective_version: Mapped[int] = mapped_column(
  72:         Integer, nullable=False, default=1
  73:     )
  74:     outcome_version: Mapped[int] = mapped_column(
  75:         Integer, nullable=False, default=1
  76:     )
  77: 
  78:     objective_type: Mapped[str] = mapped_column(
  79:         String(100), nullable=False, index=True
  80:     )
  81:     order_ref: Mapped[str] = mapped_column(
  82:         String(255), nullable=False, index=True
  83:     )
  84:     decision: Mapped[str] = mapped_column(
  85:         String(32), nullable=False, index=True
  86:     )
  87:     status: Mapped[str] = mapped_column(
  88:         String(32), nullable=False, index=True
  89:     )
  90:     operation_count: Mapped[int] = mapped_column(
  91:         Integer, nullable=False
  92:     )
  93:     customer_message: Mapped[str] = mapped_column(
  94:         Text, nullable=False
  95:     )
  96: 
  97:     operations_json: Mapped[list] = mapped_column(
  98:         JSONB, nullable=False, default=list
  99:     )
 100:     outcome_json: Mapped[dict] = mapped_column(
 101:         JSONB, nullable=False
 102:     )
 103: 
 104:     recording_idempotency_key: Mapped[str | None] = mapped_column(
 105:         String(255), nullable=True, index=True
 106:     )
 107:     created_at: Mapped[datetime] = mapped_column(
 108:         DateTime(timezone=True), nullable=False, server_default=func.now()
 109:     )
 110: 
 111: 
 112: class CustomerSupportOutcomeEvaluationRecord(Base):
 113:     """
 114:     Immutable deterministic evaluation of one canonical support outcome.
 115: 
 116:     evaluation_version allows evaluation rules to evolve without rewriting
 117:     historical conclusions.
 118:     """
 119: 
 120:     __tablename__ = "cs_support_outcome_evaluations"
 121:     __table_args__ = (
 122:         UniqueConstraint(
 123:             "user_id",
 124:             "support_outcome_id",
 125:             "evaluation_version",
 126:             name=(
 127:                 "uq_cs_support_outcome_eval_"
 128:                 "user_outcome_version"
 129:             ),
 130:         ),
 131:         Index(
 132:             "ix_cs_support_outcome_eval_user_created",
 133:             "user_id",
 134:             "created_at",
 135:         ),
 136:         Index(
 137:             "ix_cs_support_outcome_eval_user_result_created",
 138:             "user_id",
 139:             "result",
 140:             "created_at",
 141:         ),
 142:     )
 143: 
 144:     id: Mapped[uuid.UUID] = mapped_column(
 145:         UUID(as_uuid=True),
 146:         primary_key=True,
 147:         default=uuid.uuid4,
 148:     )
 149: 
 150:     user_id: Mapped[uuid.UUID] = mapped_column(
 151:         UUID(as_uuid=True),
 152:         nullable=False,
 153:         index=True,
 154:     )
 155: 
 156:     support_outcome_id: Mapped[uuid.UUID] = mapped_column(
 157:         UUID(as_uuid=True),
 158:         ForeignKey(
 159:             "cs_support_outcomes.id",
 160:             name="fk_cs_support_outcome_eval_outcome",
 161:             ondelete="CASCADE",
 162:         ),
 163:         nullable=False,
 164:         index=True,
 165:     )
 166: 
 167:     review_plan_id: Mapped[str] = mapped_column(
 168:         String(128),
 169:         nullable=False,
 170:         index=True,
 171:     )
 172: 
 173:     workflow_run_id: Mapped[uuid.UUID] = mapped_column(
 174:         UUID(as_uuid=True),
 175:         nullable=False,
 176:         index=True,
 177:     )
 178: 
 179:     evaluation_version: Mapped[int] = mapped_column(
 180:         Integer,
 181:         nullable=False,
 182:         default=1,
 183:     )
 184: 
 185:     result: Mapped[str] = mapped_column(
 186:         String(64),
 187:         nullable=False,
 188:         index=True,
 189:     )
 190: 
 191:     reason_code: Mapped[str] = mapped_column(
 192:         String(128),
 193:         nullable=False,
 194:         index=True,
 195:     )
 196: 
 197:     summary: Mapped[str] = mapped_column(
 198:         Text,
 199:         nullable=False,
 200:     )
 201: 
 202:     confidence: Mapped[float] = mapped_column(
 203:         Float,
 204:         nullable=False,
 205:     )
 206: 
 207:     retryable: Mapped[bool] = mapped_column(
 208:         nullable=False,
 209:         default=False,
 210:         index=True,
 211:     )
 212: 
 213:     achieved_operation_count: Mapped[int] = mapped_column(
 214:         Integer,
 215:         nullable=False,
 216:         default=0,
 217:     )
 218: 
 219:     failed_operation_count: Mapped[int] = mapped_column(
 220:         Integer,
 221:         nullable=False,
 222:         default=0,
 223:     )
 224: 
 225:     pending_operation_count: Mapped[int] = mapped_column(
 226:         Integer,
 227:         nullable=False,
 228:         default=0,
 229:     )
 230: 
 231:     unknown_operation_count: Mapped[int] = mapped_column(
 232:         Integer,
 233:         nullable=False,
 234:         default=0,
 235:     )
 236: 
 237:     not_executed_operation_count: Mapped[int] = mapped_column(
 238:         Integer,
 239:         nullable=False,
 240:         default=0,
 241:     )
 242: 
 243:     observed_outcome_json: Mapped[dict] = mapped_column(
 244:         JSONB,
 245:         nullable=False,
 246:         default=dict,
 247:     )
 248: 
 249:     evidence_json: Mapped[list] = mapped_column(
 250:         JSONB,
  ... (9 more lines truncated)

## B. customer_support_outcome_recording.py (runtime node) — when/how does this fire?

=== app/domains/customer_service/runtime/nodes/customer_support_outcome_recording.py (68 lines) ===
   1: from __future__ import annotations
   2: 
   3: from typing import Any, Literal
   4: from uuid import UUID
   5: 
   6: from pydantic import BaseModel, Field
   7: 
   8: from app.domains.customer_service.services.support.outcome.customer_support_outcome import CustomerSupportOutcome
   9: from app.domains.customer_service.services.support.outcome.customer_support_outcome_recording import (
  10:     CustomerSupportOutcomeRecordingService,
  11: )
  12: 
  13: 
  14: class CustomerSupportOutcomeRecordingConfig(BaseModel):
  15:     node_type: Literal["customer_service.record_support_outcome"] = (
  16:         "customer_service.record_support_outcome"
  17:     )
  18:     outcome_key: str = Field(default="support_outcome")
  19:     support_review_key: str = Field(default="support_review")
  20:     chat_session_id_key: str = Field(default="customer_chat_session_id")
  21:     save_as: str = Field(default="recorded_support_outcome")
  22: 
  23: 
  24: class CustomerSupportOutcomeRecordingNode:
  25:     async def run(self, ctx, state: dict[str, Any], config: CustomerSupportOutcomeRecordingConfig) -> dict[str, Any]:
  26:         if ctx.db is None:
  27:             raise RuntimeError("customer_service.record_support_outcome requires a database session")
  28:         workflow_run_id = (
  29:             getattr(ctx, "workflow_run_id", None)
  30:             or state.get("workflow_run_id")
  31:             or (state.get("meta") or {}).get("workflow_run_id")
  32:         )
  33: 
  34:         if ctx.user_id is None or workflow_run_id is None:
  35:             raise ValueError(
  36:                 "customer_service.record_support_outcome "
  37:                 "requires user_id and workflow_run_id"
  38:             )
  39: 
  40:         vars_ = state.get("vars") or {}
  41:         outcome = CustomerSupportOutcome.model_validate(vars_.get(config.outcome_key))
  42:         support_review = vars_.get(config.support_review_key) or {}
  43:         review_plan = support_review.get("review_plan") or {}
  44:         source_objective_version = int(review_plan.get("source_objective_version") or 1)
  45:         chat_session_id = UUID(str(vars_.get(config.chat_session_id_key)))
  46:         runtime_meta = (ctx.node_data or {}).get("_runtime") or {}
  47: 
  48:         result = await CustomerSupportOutcomeRecordingService(ctx.db).record(
  49:             user_id=UUID(str(ctx.user_id)),
  50:             workflow_run_id=UUID(str(workflow_run_id)),
  51:             chat_session_id=chat_session_id,
  52:             outcome=outcome,
  53:             source_objective_version=source_objective_version,
  54:             recording_idempotency_key=runtime_meta.get("idempotency_key"),
  55:         )
  56: 
  57:         output = {
  58:             "outcome_id": str(result.record.id),
  59:             "created": result.created,
  60:             "event_id": str(result.event_id) if result.event_id else None,
  61:             "review_plan_id": result.record.review_plan_id,
  62:             "status": result.record.status,
  63:         }
  64:         return {
  65:             "output": output,
  66:             "patch": {"vars": {config.save_as: output}},
  67:             "meta": output,
  68:         }

## C. Does outcome recording connect to capability execution / suggested_actions at all?

---

# ai-actions round 3: is CustomerSupportOutcomeRecordingService.record() reusable for single suggested-actions?

=== app/domains/customer_service/services/support/outcome/customer_support_outcome_recording.py (142 lines) ===
   1: from __future__ import annotations
   2: 
   3: from dataclasses import dataclass
   4: from uuid import UUID
   5: 
   6: from sqlalchemy.ext.asyncio import AsyncSession
   7: 
   8: from app.domains.customer_service.models.outcomes import (
   9:     CustomerSupportOutcomeRecord,
  10: )
  11: from app.domains.customer_service.repositories.chat_repository import ChatRepository
  12: from app.domains.customer_service.repositories.customer_support_outcomes import (
  13:     CustomerSupportOutcomeRepository,
  14: )
  15: from app.domains.customer_service.services.support.outcome.customer_support_outcome import (
  16:     CustomerSupportOutcome,
  17:     SupportOutcomeStatus,
  18: )
  19: from app.platform.events.publisher import PlatformEventPublisher
  20: 
  21: 
  22: SUPPORT_OUTCOME_RECORDED_EVENT = "customer_service.support.outcome.recorded"
  23: 
  24: 
  25: @dataclass(frozen=True)
  26: class CustomerSupportOutcomeRecordingResult:
  27:     record: CustomerSupportOutcomeRecord
  28:     created: bool
  29:     event_id: UUID | None
  30: 
  31: 
  32: class CustomerSupportOutcomeRecordingService:
  33:     def __init__(self, db: AsyncSession) -> None:
  34:         self.db = db
  35:         self.repository = CustomerSupportOutcomeRepository(db)
  36:         self.chat_repository = ChatRepository(db)
  37: 
  38:     async def record(
  39:         self,
  40:         *,
  41:         user_id: UUID,
  42:         workflow_run_id: UUID,
  43:         chat_session_id: UUID,
  44:         outcome: CustomerSupportOutcome,
  45:         source_objective_version: int,
  46:         recording_idempotency_key: str | None = None,
  47:     ) -> CustomerSupportOutcomeRecordingResult:
  48:         session = await self.chat_repository.get_session(chat_session_id)
  49:         if session is None or session.user_id != user_id:
  50:             raise ValueError("Support outcome chat session ownership mismatch")
  51: 
  52:         link = await self.chat_repository.get_inbox_link_for_session(
  53:             session_id=chat_session_id
  54:         )
  55:         if link is None or link.user_id != user_id:
  56:             raise ValueError("Support outcome inbox bridge is required")
  57: 
  58:         outcome_json = outcome.model_dump(mode="json")
  59:         objective_type = self._objective_type(outcome)
  60:         status = self._aggregate_status(outcome)
  61: 
  62:         write = await self.repository.record_once(
  63:             values={
  64:                 "user_id": user_id,
  65:                 "review_plan_id": outcome.review_plan_id,
  66:                 "workflow_run_id": workflow_run_id,
  67:                 "chat_session_id": chat_session_id,
  68:                 "conversation_id": link.conversation_id,
  69:                 "objective_namespace": "customer_service.support",
  70:                 "objective_ref": outcome.review_plan_id,
  71:                 "source_objective_version": source_objective_version,
  72:                 "outcome_version": outcome.version,
  73:                 "objective_type": objective_type,
  74:                 "order_ref": outcome.order_ref,
  75:                 "decision": outcome.decision,
  76:                 "status": status,
  77:                 "operation_count": len(outcome.operations),
  78:                 "customer_message": outcome.customer_message,
  79:                 "operations_json": [
  80:                     item.model_dump(mode="json") for item in outcome.operations
  81:                 ],
  82:                 "outcome_json": outcome_json,
  83:                 "recording_idempotency_key": recording_idempotency_key,
  84:             }
  85:         )
  86: 
  87:         event_id = None
  88:         if write.created:
  89:             publish_result = await PlatformEventPublisher(self.db).publish(
  90:                 event_type=SUPPORT_OUTCOME_RECORDED_EVENT,
  91:                 source="customer_service.support_outcome",
  92:                 user_id=user_id,
  93:                 payload={
  94:                     "outcome_id": str(write.record.id),
  95:                     "review_plan_id": outcome.review_plan_id,
  96:                     "conversation_id": str(link.conversation_id),
  97:                     "chat_session_id": str(chat_session_id),
  98:                     "objective_type": objective_type,
  99:                     "decision": outcome.decision,
 100:                     "status": status,
 101:                     "operation_count": len(outcome.operations),
 102:                 },
 103:                 meta={
 104:                     "workflow_run_id": str(workflow_run_id),
 105:                     "recording_idempotency_key": recording_idempotency_key,
 106:                 },
 107:                 dispatch=True,
 108:                 commit=False,
 109:             )
 110:             event_id = publish_result["event"].id
 111: 
 112:         await self.db.commit()
 113:         await self.db.refresh(write.record)
 114:         return CustomerSupportOutcomeRecordingResult(
 115:             record=write.record,
 116:             created=write.created,
 117:             event_id=event_id,
 118:         )
 119: 
 120:     @staticmethod
 121:     def _objective_type(outcome: CustomerSupportOutcome) -> str:
 122:         types = [item.operation_type.value for item in outcome.operations]
 123:         if not types:
 124:             return "unknown"
 125:         if len(types) == 1:
 126:             return types[0]
 127:         return "multi_operation"
 128: 
 129:     @staticmethod
 130:     def _aggregate_status(outcome: CustomerSupportOutcome) -> str:
 131:         if outcome.decision == "rejected":
 132:             return SupportOutcomeStatus.REJECTED.value
 133:         statuses = [item.status for item in outcome.operations]
 134:         if any(item == SupportOutcomeStatus.FAILED for item in statuses):
 135:             return SupportOutcomeStatus.FAILED.value
 136:         if statuses and all(item == SupportOutcomeStatus.COMPLETED for item in statuses):
 137:             return SupportOutcomeStatus.COMPLETED.value
 138:         if any(item == SupportOutcomeStatus.SUBMITTED for item in statuses):
 139:             return SupportOutcomeStatus.SUBMITTED.value
 140:         if any(item == SupportOutcomeStatus.PREPARED for item in statuses):
 141:             return SupportOutcomeStatus.PREPARED.value
 142:         return SupportOutcomeStatus.UNKNOWN.value

=== app/domains/customer_service/services/support/outcome/customer_support_outcome.py (461 lines) ===
   1: from __future__ import annotations
   2: 
   3: from enum import StrEnum
   4: from typing import Any, Literal
   5: 
   6: from pydantic import BaseModel, Field
   7: 
   8: from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
   9:     SupportReviewOperation,
  10:     SupportReviewOperationType,
  11:     SupportReviewPlan,
  12: )
  13: 
  14: 
  15: class SupportOutcomeStatus(StrEnum):
  16:     REJECTED = "rejected"
  17:     PREPARED = "prepared"
  18:     SUBMITTED = "submitted"
  19:     COMPLETED = "completed"
  20:     FAILED = "failed"
  21:     UNKNOWN = "unknown"
  22: 
  23: 
  24: class SupportOperationOutcome(BaseModel):
  25:     operation_ref: str | None = None
  26:     operation_type: SupportReviewOperationType
  27:     status: SupportOutcomeStatus
  28: 
  29:     item_id: str | None = None
  30:     item_label: str | None = None
  31: 
  32:     prepared: bool = False
  33:     submitted: bool = False
  34:     completed: bool = False
  35: 
  36:     provider_result: dict[str, Any] = Field(default_factory=dict)
  37: 
  38: 
  39: class CustomerSupportOutcome(BaseModel):
  40:     version: int = 1
  41: 
  42:     review_plan_id: str
  43:     order_ref: str
  44: 
  45:     decision: Literal["approved", "rejected"]
  46: 
  47:     operations: list[SupportOperationOutcome] = Field(
  48:         default_factory=list
  49:     )
  50: 
  51:     customer_message: str
  52: 
  53: 
  54: class CustomerSupportOutcomeProjector:
  55:     """
  56:     Project durable support-review execution state into a provider-neutral
  57:     customer-service outcome.
  58: 
  59:     This service owns customer-support semantics.
  60: 
  61:     It deliberately does not:
  62:     - call Shopify or any provider,
  63:     - write chat messages,
  64:     - assume capability success means business completion,
  65:     - expose raw provider wording to the customer.
  66:     """
  67: 
  68:     _RESULT_KEY_BY_OPERATION = {
  69:         SupportReviewOperationType.WHOLE_REFUND: (
  70:             "prepare_whole_refund"
  71:         ),
  72:         SupportReviewOperationType.PARTIAL_REFUND: (
  73:             "prepare_partial_refund"
  74:         ),
  75:         SupportReviewOperationType.REPLACEMENT: (
  76:             "prepare_replacement"
  77:         ),
  78:     }
  79: 
  80:     def project(
  81:         self,
  82:         *,
  83:         review_plan_id: str,
  84:         support_review: dict[str, Any],
  85:         approval_result: bool,
  86:         prepared_operations: dict[str, Any] | None = None,
  87:     ) -> CustomerSupportOutcome:
  88:         normalized_plan_id = str(review_plan_id or "").strip()
  89:         if not normalized_plan_id:
  90:             raise ValueError("review_plan_id is required")
  91: 
  92:         review_plan_payload = support_review.get("review_plan")
  93:         if not isinstance(review_plan_payload, dict):
  94:             raise ValueError(
  95:                 "support_review.review_plan is required"
  96:             )
  97: 
  98:         review_plan = SupportReviewPlan.model_validate(
  99:             review_plan_payload
 100:         )
 101: 
 102:         if not approval_result:
 103:             return self._project_rejected(
 104:                 review_plan_id=normalized_plan_id,
 105:                 review_plan=review_plan,
 106:             )
 107: 
 108:         return self._project_approved(
 109:             review_plan_id=normalized_plan_id,
 110:             review_plan=review_plan,
 111:             prepared_operations=prepared_operations or {},
 112:         )
 113: 
 114:     def _project_rejected(
 115:         self,
 116:         *,
 117:         review_plan_id: str,
 118:         review_plan: SupportReviewPlan,
 119:     ) -> CustomerSupportOutcome:
 120:         executable_operations = self._executable_operations(
 121:             review_plan
 122:         )
 123: 
 124:         operation_outcomes = [
 125:             SupportOperationOutcome(
 126:                 operation_ref=operation.operation_ref,
 127:                 operation_type=operation.operation_type,
 128:                 status=SupportOutcomeStatus.REJECTED,
 129:                 item_id=operation.item_id,
 130:                 item_label=operation.item_label,
 131:             )
 132:             for operation in executable_operations
 133:         ]
 134: 
 135:         return CustomerSupportOutcome(
 136:             review_plan_id=review_plan_id,
 137:             order_ref=review_plan.order_ref,
 138:             decision="rejected",
 139:             operations=operation_outcomes,
 140:             customer_message=self._rejected_message(
 141:                 review_plan=review_plan,
 142:                 operations=executable_operations,
 143:             ),
 144:         )
 145: 
 146:     def _project_approved(
 147:         self,
 148:         *,
 149:         review_plan_id: str,
 150:         review_plan: SupportReviewPlan,
 151:         prepared_operations: dict[str, Any],
 152:     ) -> CustomerSupportOutcome:
 153:         executable_operations = self._executable_operations(
 154:             review_plan
 155:         )
 156: 
 157:         outcomes: list[SupportOperationOutcome] = []
 158: 
 159:         for operation in executable_operations:
 160:             result_key = self._RESULT_KEY_BY_OPERATION[
 161:                 operation.operation_type
 162:             ]
 163: 
 164:             raw_result = prepared_operations.get(result_key)
 165: 
 166:             result = (
 167:                 raw_result
 168:                 if isinstance(raw_result, dict)
 169:                 else {}
 170:             )
 171: 
 172:             status = self._normalize_status(result)
 173: 
 174:             outcomes.append(
 175:                 SupportOperationOutcome(
 176:                     operation_ref=operation.operation_ref,
 177:                     operation_type=operation.operation_type,
 178:                     status=status,
 179:                     item_id=operation.item_id,
 180:                     item_label=operation.item_label,
 181:                     prepared=(
 182:                         status
 183:                         in {
 184:                             SupportOutcomeStatus.PREPARED,
 185:                             SupportOutcomeStatus.SUBMITTED,
 186:                             SupportOutcomeStatus.COMPLETED,
 187:                         }
 188:                     ),
 189:                     submitted=(
 190:                         status
 191:                         in {
 192:                             SupportOutcomeStatus.SUBMITTED,
 193:                             SupportOutcomeStatus.COMPLETED,
 194:                         }
 195:                     ),
 196:                     completed=(
 197:                         status
 198:                         == SupportOutcomeStatus.COMPLETED
 199:                     ),
 200:                     provider_result=result,

---

# ai-actions: confirming real ShopifyRuntimeService/ShopifyService methods before writing tracking/note executors

## A. Find what 'services.business.shopify' actually resolves to (search for ShopifyRuntimeService or similar wiring)
  'ShopifyRuntimeService' found in app/runtime_services.py
  'business.shopify' found in app/providers/shopify/runtime/nodes.py
  'business.shopify' found in app/runtime/capabilities/execution/providers/shopify.py
  'business.shopify' found in app/runtime/capabilities/execution/runtime.py

## B. Full method surface of app/domains/customer_service/services/shopify.py (ShopifyService)

=== app/domains/customer_service/services/shopify.py :: ALL method signatures ===
class ShopifyService:
    def __init__(self, db, provider)  [L30]
    def connect(self)  [L39]
    def get_active_connection(self)  [L86]
    def delete_connection(self)  [L89]
    def test_connection(self)  [L118]
    def get_order(self)  [L209]
    def get_order_fresh(self)  [L289]
    def prepare_support_workflow(self)  [L334]
    def perform_order_action(self)  [L369]
    def _require_durable_approval(self)  [L515]
    def _find_shopify_action_by_idempotency_key(self)  [L557]
    def _record_shopify_action_idempotency_result(self)  [L577]
    def _order_ai_summary(self, order_read)  [L610]
    def _normalize_shop_domain(self, shop_domain)  [L658]

## C. Does perform_order_action already internally handle shipping_status / reship / tracking-like data?

--- perform_order_action (lines 369-513) ---
 369:     async def perform_order_action(
 370:         self,
 371:         *,
 372:         user_id,
 373:         action: str,
 374:         order_ref: str,
 375:         reason: str | None = None,
 376:         note: str | None = None,
 377:         new_address: dict | None = None,
 378:         amount: str | None = None,
 379:         scope: dict | None = None,
 380:         idempotency_key: str | None = None,
 381:         approval_wait_id: str | None = None,
 382:         workflow_run_id: str | None = None,
 383:     ) -> dict:
 384:         if action in {"refund", "reship"} and getattr(
 385:             self.provider, "requires_durable_approval", False
 386:         ):
 387:             await self._require_durable_approval(
 388:                 user_id=user_id,
 389:                 action=action,
 390:                 order_ref=order_ref,
 391:                 approval_wait_id=approval_wait_id,
 392:                 workflow_run_id=workflow_run_id,
 393:             )
 394:         if idempotency_key:
 395:             lock_key = f"cs_shopify_action:{user_id}:{idempotency_key}"
 396:             await self.db.execute(
 397:                 text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
 398:                 {"lock_key": lock_key},
 399:             )
 400: 
 401:             existing = await self._find_shopify_action_by_idempotency_key(
 402:                 user_id=user_id,
 403:                 idempotency_key=idempotency_key,
 404:             )
 405:             if existing is not None:
 406:                 return existing
 407: 
 408:         connection = await self.repo.get_active_connection(user_id=user_id)
 409: 
 410:         if connection is None:
 411:             raise HTTPException(
 412:                 status_code=404,
 413:                 detail="Shopify connection not found",
 414:             )
 415: 
 416:         order_read = await self.get_order(
 417:             user_id=user_id,
 418:             order_ref=order_ref,
 419:         )
 420: 
 421:         context = order_read.get("context") or {}
 422:         order = (
 423:             order_read.get("raw")
 424:             or context.get("raw")
 425:             or order_read.get("payload")
 426:             or order_read
 427:         )
 428: 
 429:         provider_kwargs = {
 430:             "shop_domain": connection.shop_domain,
 431:             "access_token": decrypt_secret(connection.access_token_encrypted),
 432:             "order": order,
 433:         }
 434: 
 435:         if action == "cancel" and context.get("can_cancel") is False:
 436:             payload = {
 437:                 "status": "blocked",
 438:                 "message": "Order cannot be cancelled in its current state",
 439:                 "reason": reason,
 440:             }
 441:         elif action == "refund":
 442:             payload = await self.provider.refund_order(
 443:                 **provider_kwargs,
 444:                 reason=reason,
 445:                 amount=amount,
 446:                 scope=scope,
 447:             )
 448:         elif action == "cancel":
 449:             payload = await self.provider.cancel_order(
 450:                 **provider_kwargs,
 451:                 reason=reason,
 452:             )
 453:         elif action == "update_shipping_address":
 454:             payload = await self.provider.change_order_address(
 455:                 **provider_kwargs,
 456:                 new_address=new_address or {},
 457:                 note=note,
 458:             )
 459:         elif action == "reship":
 460:             payload = await self.provider.reship_order(
 461:                 **provider_kwargs,
 462:                 reason=reason,
 463:                 note=note,
 464:                 scope=scope,
 465:             )
 466:         elif action == "shipping_status":
 467:             payload = {
 468:                 "status": "prepared",
 469:                 "message": "Shipping status prepared",
 470:                 "fulfillment_status": (
 471:                     order_read.get("fulfillment_status")
 472:                     or (order_read.get("context") or {}).get("fulfillment_status")
 473:                     or (order_read.get("context") or {}).get("current_status")
 474:                     or order_read.get("status")
 475:                 ),
 476:                 "tracking": order_read.get("shipping") or order_read.get("tracking"),
 477:             }
 478:         else:
 479:             raise HTTPException(
 480:                 status_code=422,
 481:                 detail=f"Unsupported Shopify action: {action}",
 482:             )
 483: 
 484:         result = {
 485:             "action": action,
 486:             "order_id": order_read["order_id"],
 487:             "order_name": order_read["order_name"],
 488:             "status": payload.get("status", "prepared"),
 489:             "message": payload.get("message", "Shopify action prepared"),
 490:             "payload": payload,
 491:             "scope": scope or {},
 492:             "idempotency_key": idempotency_key,
 493:         }
 494: 
 495:         if idempotency_key:
 496:             self.db.add(
 497:                 CustomerServiceAuditLog(
 498:                     user_id=user_id,
 499:                     entity_type="shopify_action",
 500:                     entity_id=None,
 501:                     action="executed",
 502:                     message=f"Shopify action {action} executed idempotently",
 503:                     meta={
 504:                         "idempotency_key": idempotency_key,
 505:                         "shopify_action": action,
 506:                         "order_ref": order_ref,
 507:                         "result": result,
 508:                     },
 509:                 )
 510:             )
 511:             await self.db.commit()
 512: 
 513:         return result

---

# ai-actions round 5: ShopifyProvider surface — need exact signature for change_order_address/reship_order to model add_order_note on

=== app/domains/customer_service/providers/shopify.py :: method signatures ===
class ShopifyProvider:
    def create_app_subscription(self)  [L7]
    def get_active_app_subscriptions(self)  [L9]
    def cancel_app_subscription(self)  [L11]
    def verify_connection(self)  [L13]
    def get_order(self)  [L20]
    def list_knowledge_content(self)  [L28]
    def refund_order(self)  [L32]
    def cancel_order(self)  [L43]
    def change_order_address(self)  [L52]
    def reship_order(self)  [L62]
    def report_damaged_item(self)  [L73]
    def get_shipping_status(self)  [L83]
class FakeShopifyProvider:
    def create_app_subscription(self)  [L93]
    def get_active_app_subscriptions(self)  [L99]
    def cancel_app_subscription(self)  [L102]
    def verify_connection(self)  [L105]
    def get_order(self)  [L120]
    def list_knowledge_content(self)  [L138]
    def refund_order(self)  [L143]
    def cancel_order(self)  [L163]
    def change_order_address(self)  [L189]
    def reship_order(self)  [L217]
    def report_damaged_item(self)  [L237]
    def get_shipping_status(self)  [L255]

--- app/domains/customer_service/providers/shopify.py :: def cancel_order (lines 43-50) ---
  43:     async def cancel_order(
  44:         self,
  45:         *,
  46:         shop_domain: str,
  47:         access_token: str | None,
  48:         order: dict,
  49:         reason: str | None,
  50:     ) -> dict: ...

--- app/domains/customer_service/providers/shopify.py :: def change_order_address (lines 52-60) ---
  52:     async def change_order_address(
  53:         self,
  54:         *,
  55:         shop_domain: str,
  56:         access_token: str | None,
  57:         order: dict,
  58:         new_address: dict,
  59:         note: str | None,
  60:     ) -> dict: ...

--- app/domains/customer_service/providers/shopify.py :: def reship_order (lines 62-71) ---
  62:     async def reship_order(
  63:         self,
  64:         *,
  65:         shop_domain: str,
  66:         access_token: str | None,
  67:         order: dict,
  68:         reason: str | None,
  69:         note: str | None,
  70:         scope: dict | None = None,
  71:     ) -> dict: ...

--- app/domains/customer_service/providers/shopify.py :: def cancel_order (lines 163-187) ---
 163:     async def cancel_order(
 164:         self,
 165:         *,
 166:         shop_domain: str,
 167:         access_token: str | None,
 168:         order: dict,
 169:         reason: str | None,
 170:     ) -> dict:
 171:         fulfillment_status = order.get("fulfillment_status")
 172:         if fulfillment_status == "fulfilled":
 173:             return {
 174:                 "status": "blocked",
 175:                 "message": "Order is already fulfilled and cannot be auto-cancelled",
 176:                 "reason": reason,
 177:                 "shop_domain": shop_domain,
 178:                 "order_id": str(order.get("id")),
 179:             }
 180: 
 181:         return {
 182:             "status": "prepared",
 183:             "message": "Cancellation request prepared for review",
 184:             "reason": reason,
 185:             "shop_domain": shop_domain,
 186:             "order_id": str(order.get("id")),
 187:         }

--- app/domains/customer_service/providers/shopify.py :: def change_order_address (lines 189-215) ---
 189:     async def change_order_address(
 190:         self,
 191:         *,
 192:         shop_domain: str,
 193:         access_token: str | None,
 194:         order: dict,
 195:         new_address: dict,
 196:         note: str | None,
 197:     ) -> dict:
 198:         if order.get("fulfillment_status") == "fulfilled":
 199:             return {
 200:                 "status": "blocked",
 201:                 "message": "Order is already fulfilled and address cannot be changed automatically",
 202:                 "new_address": new_address,
 203:                 "note": note,
 204:                 "shop_domain": shop_domain,
 205:                 "order_id": str(order.get("id")),
 206:             }
 207: 
 208:         return {
 209:             "status": "prepared",
 210:             "message": "Address change request prepared for review",
 211:             "new_address": new_address,
 212:             "note": note,
 213:             "shop_domain": shop_domain,
 214:             "order_id": str(order.get("id")),
 215:         }

--- app/domains/customer_service/providers/shopify.py :: def reship_order (lines 217-235) ---
 217:     async def reship_order(
 218:         self,
 219:         *,
 220:         shop_domain: str,
 221:         access_token: str | None,
 222:         order: dict,
 223:         reason: str | None,
 224:         note: str | None,
 225:         scope: dict | None = None,
 226:     ) -> dict:
 227:         return {
 228:             "status": "prepared",
 229:             "message": "Replacement shipment prepared for review",
 230:             "reason": reason,
 231:             "note": note,
 232:             "scope": scope or {},
 233:             "shop_domain": shop_domain,
 234:             "order_id": str(order.get("id")),
 235:         }

---

# ai-actions round 6: get_shipping_status + report_damaged_item bodies (both provider abstract + fake impl)

--- app/domains/customer_service/providers/shopify.py :: def report_damaged_item (lines 73-81) ---
  73:     async def report_damaged_item(
  74:         self,
  75:         *,
  76:         shop_domain: str,
  77:         access_token: str | None,
  78:         order: dict,
  79:         reason: str | None,
  80:         note: str | None,
  81:     ) -> dict: ...

--- app/domains/customer_service/providers/shopify.py :: def get_shipping_status (lines 83-89) ---
  83:     async def get_shipping_status(
  84:         self,
  85:         *,
  86:         shop_domain: str,
  87:         access_token: str | None,
  88:         order: dict,
  89:     ) -> dict: ...

--- app/domains/customer_service/providers/shopify.py :: def report_damaged_item (lines 237-253) ---
 237:     async def report_damaged_item(
 238:         self,
 239:         *,
 240:         shop_domain: str,
 241:         access_token: str | None,
 242:         order: dict,
 243:         reason: str | None,
 244:         note: str | None,
 245:     ) -> dict:
 246:         return {
 247:             "status": "prepared",
 248:             "message": "Damaged item case prepared for support review",
 249:             "reason": reason,
 250:             "note": note,
 251:             "shop_domain": shop_domain,
 252:             "order_id": str(order.get("id")),
 253:         }

--- app/domains/customer_service/providers/shopify.py :: def get_shipping_status (lines 255-266) ---
 255:     async def get_shipping_status(
 256:         self, *, shop_domain: str, access_token: str | None, order: dict
 257:     ) -> dict:
 258:         return {
 259:             "status": "found",
 260:             "message": "Shipping status found",
 261:             "fulfillment_status": order.get("fulfillment_status"),
 262:             "tracking_number": order.get("tracking_number"),
 263:             "tracking_url": order.get("tracking_url"),
 264:             "shop_domain": shop_domain,
 265:             "order_id": str(order.get("id")),
 266:         }

## Is get_shipping_status called ANYWHERE in the codebase currently?
  app/domains/customer_service/integrations/shopify/real_provider.py:550: async def get_shipping_status(
  app/domains/customer_service/providers/shopify.py:83: async def get_shipping_status(
  app/domains/customer_service/providers/shopify.py:255: async def get_shipping_status(

---

## PROGRESS TRACKER (live status — updated as work completes)

### Corrections to original audit (confirmed via code inspection)
- Task "Create ActionExecution model in commercial.py" — CORRECTED: a similar but incompatible model (`CustomerSupportOutcomeRecord`) already exists, scoped to the planner/review-plan pipeline only (requires chat_session_id, tied to WHOLE_REFUND/PARTIAL_REFUND/REPLACEMENT operation types). It cannot be reused for suggested_actions' single-action executions. Real new model still needed, but as its own file `app/domains/customer_service/models/capability_executions.py`, not stuffed into commercial.py, and named to avoid confusion with the existing outcome record (e.g. `CapabilityExecutionRecord`).
- Task "tracking capability calls shopify.get_order_tracking(...)" — CORRECTED: no new provider method needed. `ShopifyProvider.get_shipping_status()` already exists, fully implemented in both FakeShopifyProvider and the real provider (real_provider.py:550), and returns tracking_number/tracking_url/fulfillment_status. It was simply never called — dead code.

### REAL BUG FOUND AND FIXED (not in original audit)
`perform_order_action`'s `shipping_status` branch (app/domains/customer_service/services/shopify.py) was hand-building a partial response dict instead of calling the already-implemented `self.provider.get_shipping_status(...)`. Result: tracking_number and tracking_url were always None even though the provider layer fully supported them.
- FIXED: replaced inline dict with `await self.provider.get_shipping_status(**provider_kwargs)`
- VERIFIED: full test suite run (tests/customer_service/shopify/ + related runtime/realtime tests) — 102 passed, 0 failed, 0 regressions

### REAL BUG FOUND AND FIXED (round 8, continuation session)
`ShopifyRuntimeService.perform_order_action` (app/runtime_services.py) was missing
`approval_wait_id` and `workflow_run_id` from its signature and its delegated call to
`ShopifyService.perform_order_action`, even though `ShopifyOrderActionNode.run()`
(app/providers/shopify/runtime/nodes.py) unconditionally passes both. This broke every
live execution of a `shopify_action` workflow node with a TypeError -- including the
durable-approval resume path for refund/reship (confirmed via
test_pending_complex_objective_resumes_from_customer_clarification, which failed until
fixed). Existing regression coverage missed it because
tests/runtime/test_runtime_shopify_nodes.py only tested the early order_ref ValueError
guard, never a real call through to perform_order_action.
- FIXED: added both params to ShopifyRuntimeService.perform_order_action's signature
  and forwarded them in the delegated call.
- Added test_shopify_order_action_calls_perform_order_action_with_expected_kwargs
  (tests/runtime/test_runtime_shopify_nodes.py) asserting the real kwargs reach the
  service, not just the guard clause.
- Two stale test stubs with narrower hardcoded signatures had to be updated to match:
  tests/customer_service/chat/test_complex_support_intake_e2e.py
  (capture_perform_order_action) and
  tests/runtime/contracts/test_application_shopify_runtime_service.py
  (fake_perform_order_action).
- VERIFIED: full suite, 2356 passed, 0 failed.

### CRITICAL ARCHITECTURAL GAP (round 8): verification is unreachable from suggested_actions.py's actual execution path
The string "shopify.order_action" is used for two unrelated things in this codebase:
(1) a provider_ref in the capability-registry binding for `ecommerce.orders.action`,
bound with runtime_node_type="capability.invoke" -- this is what the round-6
verification work (ShopifyAddressChangePreparationVerifier, ShopifyReshipPreparationVerifier,
build_task_verification_context gate) correctly wired and verified, via CapabilityInvoker /
CapabilityInvocation / CapabilityResult. (2) a separate workflow NODE TYPE, registered in
app/providers/shopify/runtime/registration.py (ShopifyOrderActionNode), used directly by
the workflow templates in shopify_workflow_catalog.py that suggested_actions.py's
ShopifyActionWorkflowService.start_action_workflow actually emits.

ShopifyOrderActionNode.run() calls shopify.perform_order_action(...) directly. It never
constructs a CapabilityInvocation and never goes through CapabilityInvoker. This means
build_task_verification_context / the verifier registry / TaskVerificationService never
run for ANY suggested-action-originated Shopify call -- refund and cancel included, not
just the newer update_shipping_address/reship work. The round-6 "VERIFIED end-to-end via
live capability-system introspection" claim is accurate for path (1) but does not apply
to path (2), which is the one actually used in production by suggested actions.

Two ways to close this, not yet decided:
(a) Change start_action_workflow's templates to use a capability.invoke node bound to
    ecommerce.orders.action instead of the standalone shopify.order_action node type --
    routes suggested actions through the already-verified capability path. Larger,
    touches shopify_workflow_catalog.py template JSON and possibly payload shape
    (ShopifyOrderActionConfig.action uses "change_address"; the capability binding's
    supported_actions list uses "update_shipping_address" -- these would need to agree).
(b) Leave the two paths separate and treat verification as genuinely out of scope for
    suggested-action executions for now; design CapabilityExecutionRecord to record an
    honest "verification: not_applicable" status for this path rather than implying
    verification ran.
RESOLVED (round 9, this session) for `cancel` only -- see below. `refund` and `reship`
remain on the unverified path deliberately, because both are gated by
ShopifyService.perform_order_action's durable-approval check
(`if action in {"refund", "reship"} and provider.requires_durable_approval`), and
CapabilityInvocation has no field for approval_wait_id/workflow_run_id -- routing
refund/reship through capability.invoke today would hard-fail every real-provider
execution with HTTPException(409) (requires_durable_approval=True on
app/domains/customer_service/integrations/shopify/real_provider.py, the actual
production provider). This is a structural gap in CapabilityInvocation itself, not
specific to suggested_actions.py -- CustomerSupportOperationGraphBuilder (the
review-plan/repair pipeline) already routes whole_refund/partial_refund/replacement
(reship) through capability.invoke the same broken way, with zero test coverage of
requires_durable_approval=True anywhere in the suite. This affects live refunds/reships
processed through the review-plan pipeline against the real Shopify provider today,
independent of suggested_actions.py. FOLLOW-UP (not done, larger/riskier than today's
scope): add approval_wait_id/workflow_run_id to CapabilityInvocation, thread them
through CapabilityInvokeNode.run() (source from ctx/state, matching how
ShopifyOrderActionNode does it) and execute_shopify_order_action, then verify against
a test that actually exercises requires_durable_approval=True end-to-end (none exists
today). Once that's fixed, refund/reship can move to capability.invoke the same way
cancel did below.

### FIXED (round 9, this session): cancel now routes through capability.invoke and is verified
Changed only the "cancel" action's node in shopify_workflow_catalog.py's _template()
(shopify_action node) from the standalone shopify.order_action node type to
capability.invoke bound to ecommerce.orders.action -- refund/damaged_item/shipping_status
untouched, still on the old node type. Added a matching mutation branch in
shopify_action_workflows.py's _workflow_from_template() for the new node shape
(writes into data["config"]["payload"] instead of flat data fields; embeds a static
idempotency_key f"cs:shopify:cancel:{order_ref}", matching the pattern
CustomerSupportOperationGraphBuilder already uses for its capability.invoke nodes,
since capability.invoke has no idempotency handling of its own).

Verified safe before writing: confirmed RuntimeServices.capabilities is populated for
every workflow.run job (build_application_runtime_services -> RuntimeServiceFactory.build
sets services.capabilities = CapabilityInvoker(...); workflow_jobs.py's
run_workflow_job/resume_workflow_job route through this via
build_application_runtime_context). Confirmed cancel is not in perform_order_action's
{"refund","reship"} durable-approval gate, so the CapabilityInvocation approval-context
gap above does not affect cancel. Confirmed no test asserts on the old node shape for
the cancellation template specifically (only name/count/status metadata is checked by
test_customer_service_shopify_workflow_templates.py).

New tests added:
- tests/customer_service/shopify/test_shopify_cancel_capability_routing.py --
  structural: asserts the cancel template dispatches a capability.invoke node with the
  right capability_id/input_from/input_key/payload/idempotency_key, and that refund is
  untouched (still shopify.order_action).
- tests/runtime/test_capability_invoke_node_shopify_cancel.py -- node-execution level:
  drives CapabilityInvokeNode.run() directly against a recording fake capabilities
  service, proving vars.order_ref merges correctly into CapabilityInvocation.inputs
  alongside the static config.payload fields.

VERIFIED: full suite, 2359 passed (2356 + 3 new), 0 failed.

Net effect: suggested-actions-originated Shopify cancellations are now genuinely
verified end-to-end (ShopifyCancelOutcomeVerifier re-reads order state via
get_order_fresh and confirms cancelled_at is set) for the first time. Refund, reship,
damaged_item, and shipping_status remain unverified from this entry point, for the
reasons above.

### Task list status
- [x] Fix shipping_status to use existing get_shipping_status provider method (bug fix, done + tested)
- [x] Register `ecommerce.orders.tracking` as SAFE, no-approval capability — DONE. New executor execute_shopify_get_order_tracking reuses the fixed shipping_status path. VERIFIED end-to-end: capability registered (risk=safe), binding correct, alias resolves both directions, executor present. Confirmed via live build_default_system() introspection + full tests/runtime/contracts/ suite (63 passed, 0 regressions).
- [x] Add add_order_note — DONE. Decided: separate capability `ecommerce.orders.add_note` (MEDIUM risk, requires_approval=False), not folded into ecommerce.orders.action, because that capability's risk is fixed at HIGH/approval-required with no per-action override mechanism (confirmed: requires_approval is always set explicitly per-binding, never derived from risk). Added: (a) add_order_note to ShopifyProvider ABC + FakeShopifyProvider, (b) add_note branch in perform_order_action with empty-note validation, (c) new executor execute_shopify_add_order_note, (d) manifest capability+binding+alias. VERIFIED end-to-end via live system introspection (capability, binding, alias, executor all confirmed present and correct) + full regression suite: 884 passed, 0 failed.
  - Side fix: updated tests/runtime/contracts/test_capability_executor_coverage.py's two hardcoded provider_ref tuples (stale snapshot assertions, alphabetically sorted) to include the two new refs.
  - NOTE: real_provider.py (production Shopify integration) does NOT yet have add_order_note implemented — only the ABC + Fake. This is expected: FakeShopifyProvider is what tests exercise; real_provider.py needs its own add_order_note before this capability works against live Shopify. Flagging as follow-up, not blocking v1 capability-layer completeness.
- [x] Add verifiers for update_shipping_address and reship — DONE. CRITICAL discovery: registering a verifier alone would have been dead code. `build_task_verification_context()` (app/runtime/capabilities/execution/outcomes.py) hardcodes a gate that only builds a verification context for action in {cancel, refund} under provider_ref=="shopify.order_action" — everything else returns None before ever reaching the verifier registry. Fixed properly: (1) extended the gate to include update_shipping_address and reship with honest "prepared, not submitted" expected_outcome shapes matching the real provider behavior (change_order_address/reship_order never submit to Shopify, only prepare), (2) added ShopifyAddressChangePreparationVerifier and ShopifyReshipPreparationVerifier following the exact ShopifyRefundPreparationVerifier pattern, (3) registered both in register_shopify_task_verifiers(). VERIFIED: full suite 884 passed. Fixed one stale test (test_task_verifier_registry_rejects_unknown_action used "reship" as its "definitely unregistered" example — swapped to "shipping_status", which is still genuinely unregistered by design, see scope note below).

  SCOPE DECISION — tracking and add_note verification intentionally NOT implemented: their capabilities use different provider_refs (shopify.get_order_tracking, shopify.add_order_note) than shopify.order_action, so they'd need their own branch in build_task_verification_context. Tracking is a pure read with nothing meaningful to verify beyond "did the read succeed" (implicit in execution success). Add-note's success is weakly observable at best (unconfirmed whether FakeShopifyProvider/real order shape exposes notes for re-reading) and was not implemented to avoid a verifier that provides false confidence. Flagging as explicit follow-up if product requires it, not silently skipped.
- [ ] New model: CapabilityExecutionRecord (renamed from ActionExecution) in new file app/domains/customer_service/models/capability_executions.py, following the exact immutable+idempotency-key+platform-event pattern proven in CustomerSupportOutcomeRecord/CustomerSupportOutcomeRecordingService — new migration required
- [ ] Wire suggested_actions.py to write CapabilityExecutionRecord after verification (confirmed zero existing outcome-recording hooks there — genuinely new wiring)
- [ ] Error recovery logic (_assess_recovery_action) — as per original audit, no changes needed to that task
- [ ] E2E tests for full lifecycle + failure recovery, modeled on existing review-plan outcome tests' structure


---

# ai-actions round 7: does ProviderBinding support fixed/default input injection (so tracking can reuse order_action without a new executor)?

--- ProviderBinding (lines 64-80) ---
  64: class ProviderBinding(BaseModel):
  65:     capability_id: str
  66:     provider_id: str
  67: 
  68:     provider_ref: str
  69:     runtime_node_type: str = "capability.invoke"
  70: 
  71:     required_inputs: tuple[str, ...] = ()
  72:     optional_inputs: tuple[str, ...] = ()
  73:     output_key: str | None = None
  74: 
  75:     priority: int = 100
  76:     enabled: bool = True
  77:     risk: CapabilityRisk = CapabilityRisk.SAFE
  78:     requires_approval: bool = False
  79: 
  80:     metadata: dict[str, Any] = Field(default_factory=dict)