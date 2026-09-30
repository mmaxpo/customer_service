# Feature: AI Customer-Service Agent

## Spec
- **What it should do:** Understand a customer request, gather relevant context, decide what should happen, and produce an appropriate response or escalation.
- **Layer:** core
- **Likely location (guess — verify, I don't have your repo):** app/tcos planner/agent loop (understand → retrieve → decide → act/answer/escalate → verify)
- **Key entities:** AI Interaction, Intent, Entity, AI Decision, AI Response, AI Action, AI Escalation, AI Summary
- **Core rules to check against:** AI cannot access another tenant; cannot perform unauthorized capabilities; must not claim an action succeeded without verification; should ask for clarification when required; should escalate when confidence/context is insufficient; decisions and important actions observable

## Acceptance criteria (from the v1 spec's "DONE" list)
- Understands supported v1 intents; identifies customer/order; retrieves relevant context
- Can answer, ask clarification, invoke supported actions, escalate
- Generates human-readable summaries; does not falsely claim success
- Outcomes recorded; tests cover representative customer scenarios

## Production success condition
> Tajeran can autonomously handle defined customer-service scenarios while safely escalating anything outside its reliable operating boundary.

## Audit Result
_Filled in by `/audit-feature ai-customer-service-agent`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- **Agent runtime** (`app.agents_runtime/`) — tool-based agent loop with LLM calls, tool invocation, event recording, state persistence, usage tracking, approval workflows (max 8 steps default)
- **Customer Support Product Planner** (`app/domains/customer_service/services/support/planning/`) — classifies messages (SHIPPING, GENERAL intents), interprets objectives, builds planning operations for order status lookup and reply generation
- **Message Classifier** — classifies into SupportIntent enum (SHIPPING, GENERAL, others)
- **Autopilot Service** — policies with confidence thresholds and risk caps (low/medium/high/critical) to auto-send replies or require approval
- **AI Reply Composer** — generates Shopify order tracking replies with hardcoded templates
- **Conversation Intelligence** — gathers context from conversations (intent, sentiment, urgency)
- **Agent Assist API** (`/customer-service/conversations/{id}/agent-assist/reply-suggestion`) — endpoint for reply suggestions
- **Tests** — basic agent_assist reply suggestion tests covering reply generation

**Is it good enough?**
- **Partial.** Core understand→retrieve→decide→act→verify flow exists, but several critical v1 requirements are weak or missing:
  - Understands basic v1 intents (shipping inquiry, general questions) ✓
  - Retrieves relevant context (order info, conversation history) ✓
  - Can answer & invoke actions (reply generation, order lookup) ✓
  - **Missing:** explicit escalation when confidence < threshold; no verification that actions actually succeeded (e.g., reply was sent); clarification flows built into planner but UX unclear; knowledge integration not deeply tested
  - **Boundary violation:** `customer_service/services/` imports `app.runtime.*` and `app.tcos.*` directly (see CLAUDE.md boundary list)

**Gaps / risks:**
- **Verification weakness:** Autopilot policies check confidence & risk only; does not verify action success before claiming it. No "did the reply actually send?" confirmation. Risk: false claims in response.
- **Escalation missing:** No clear escalation path when confidence < minimum threshold or required context is missing. Planner returns clarification state but not surfaced in reply suggestion UX.
- **Limited scope:** Only handles order tracking & general replies. Other v1 intents (refund, cancellation, damaged item) only have autopilot policies, not implemented in planner/agent.
- **Clarification state handling:** Planner can return `ProductPlanningClarification` (e.g., missing order number) but agent API doesn't expose clarification requests to user—falls through to fallback reply.
- **Knowledge integration:** Knowledge search operation in general reply plan but unclear if it's actually executed or how results are merged into LLM context.
- **Tenant isolation:** Autopilot/planner check workspace_id, but verify all paths (event store, state store, conversation retrieval) enforce tenant isolation.
- **Test coverage:** Only reply suggestion tested; no tests for escalation decisions, clarification requests, failed action handling, or cross-tenant scenarios.
- **Summary generation:** No explicit summary generation logic found (acceptance criteria mentioned "generates human-readable summaries").

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] **Verification:** Add success verification to agent loop — after tool execution, check result.success or equivalent before LLM sees result. If failed, emit TOOL_CALL_FAILED event and include error in next LLM turn so it can escalate.
- [ ] **Escalation on low confidence:** Modify `CustomerServiceAutopilotService.evaluate()` to return escalation decision (not just draft/auto_send/require_approval) when confidence < threshold. Update planner clarification UX to expose missing-field errors to reply-suggestion caller.
- [ ] **Expand scope:** Add planners for refund_request, cancellation_request, damaged_item intents (currently only have autopilot policies). Each should follow same understand→retrieve→decide→act pattern.
- [ ] **Knowledge integration:** Verify knowledge search tool is registered and executed in general reply plan; add test asserting knowledge results are passed to reply generation operation.
- [ ] **Tenant isolation audit:** Grep for workspace_id checks in `event_store.py`, `state_store.py`, conversation retrieval calls; verify no leaks across workspaces.
- [ ] **Clarification UX:** Modify `/customer-service/conversations/{id}/agent-assist/reply-suggestion` to check `plan_result.requires_clarification` and return `{"status": "needs_clarification", "missing_fields": [...]}` instead of falling through to default reply.
- [ ] **Summary generation:** Add explicit step in agent loop: after action sequence completes, call LLM with "summarize the conversation outcome in 1-2 sentences for human review" instruction. Store in agent state/event.
- [ ] **Test coverage:** Add tests for: (1) escalation on low confidence, (2) clarification request when order number missing, (3) verification failure scenarios, (4) cross-tenant isolation, (5) all four intent types (shipping, general, refund, cancellation, damaged).
- [ ] **Boundary cleanup:** Move product planner logic to `app/domains/` layer; ensure it uses `ProductPlannerRegistry` to register itself, not direct `app.runtime.*` imports inside services. 
