# Feature: AI → Human Handoff

## Spec
- **What it should do:** AI can escalate a conversation with enough recorded context (why, what was tried, what failed, recommended next action) that a human can continue immediately.
- **Layer:** cross-layer (core AI loop → product conversation state)
- **Likely location (guess — verify, I don't have your repo):** app/tcos escalation logic + domains/customer_service conversation assignment
- **Key entities:** Escalation, Conversation, AI Summary, Handoff, Assignment
- **Core rules to check against:** Escalation preserves conversation history; human must see AI context; AI must stop acting when human control is active unless explicitly allowed; returning control to AI must be explicit

## Acceptance criteria (from the v1 spec's "DONE" list)
- AI can escalate with reason, summary, attempted actions visible
- Human can take over; AI stops appropriately
- Human can resolve or return control to AI
- Tests cover handoff state transitions

## Production success condition
> A human can take over an AI-handled conversation without repeating the investigation already performed by AI.

## Audit Result
_Filled in by `/audit-feature ai-human-handoff`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- **Handoff settings** (`app/domains/customer_service/models/chat.py`): ChatWidgetSettings has `human_handoff_enabled` (boolean, default True) and `human_handoff_message` (string, default "I'll connect you with our support team now."). Accessible via `/customer-service/channels/{channel_id}` API.
- **Escalation action** (`app/domains/customer_service/services/suggested_actions.py:execute_action`): SuggestedAction with `action_type="escalate"` updates the associated ticket to priority="urgent", status="pending", and adds a "escalated" tag to the conversation.
- **Escalation as suggested action** (`suggested_actions.py:_build_suggested_actions`): Escalation can be suggested based on conversation sentiment (negative) or urgency (high), with payload containing reason.
- **No-answer policy** (`app/domains/customer_service/models/management.py`, `knowledge.py`): Merchant can set no_answer_policy to "handoff" (default), "clarify", or "draft_only". When knowledge search returns no hits, AI can trigger handoff based on this policy.
- **Assignment** (`app/domains/customer_service/services/assignment.py`, `inbox.py`): TicketAssignmentRepository and AssignmentService enable POST /{ticket_id}/assign with assigned_to user_id. Creates notification to assignee.
- **Conversation state** (`app/domains/customer_service/models/core.py`): Conversation model has status field (OPEN, PENDING, RESOLVED). Ticket has assigned_to field tracking which user is assigned.
- **Tests**: Chat widget handoff settings CRUD tested (`test_customer_service_chatbot_automation_controls.py`), LLM fallback with handoff flag tested (`test_llm_provider_resilience.py`).

**Is it good enough?**
No. Core infrastructure exists but feature is **incomplete for v1**. **Five critical gaps:**
1. **No AI pause on escalation**: Escalate action marks ticket urgent and adds tag, but there is no mechanism to stop AI from continuing to process messages in that conversation. The AI loop never checks "is this conversation assigned to a human?" before generating replies.
2. **No explicit handoff state**: Conversation.status is OPEN/PENDING/RESOLVED, but there's no field or state indicating "human control active" or "awaiting human response." Assignment info lives only on Ticket, not on Conversation.
3. **No AI context summary for human**: When escalation occurs, no AI summary (what was tried, why it failed, recommended next action) is generated or attached to the conversation/ticket for the human to see. Escalate action only sets metadata, no context blob.
4. **No human → AI control relinquishment**: There's no API or mechanism for a human to explicitly say "return this to AI" or "re-engage AI mode." Once assigned to a human, the AI may never touch it again.
5. **No test coverage for handoff state transitions**: No test verifies (a) AI stops replying after escalation, (b) human sees AI context, (c) human can return control to AI, (d) AI resumes after relinquishment.

**Gaps / risks:**
- **Silent AI continuation**: A merchant escalates a conversation to urgent. Meanwhile, the AI's workflow loop continues running, potentially generating more replies after the human takes over. Two agents (AI and human) may write simultaneously.
- **Lost context**: When a human joins, they see only the message history, not why the AI escalated, what it tried, or what it recommends next. They must re-read the entire thread.
- **Deadlock after escalation**: Once escalated, there's no documented way for a human to un-escalate and resume AI handling if they determine the issue was simpler than expected.
- **No audit trail for escalation**: Escalate action adds a tag and updates ticket priority, but doesn't log who escalated, when, or why in a structured way (metadata is in SuggestedAction.payload only).
- **Handoff settings mismatch**: Chat widget has human_handoff_enabled, but this is not wired into any decision gate. Reaching human_handoff_message to a customer is not automatic; it requires manual detection or explicit trigger.

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add AI pause state to Conversation model: in `app/domains/customer_service/models/core.py`, add a field `ai_paused: Mapped[bool] = mapped_column(Boolean, default=False, index=True)` to track when human control is active. Add `ai_paused_reason: Mapped[str | None] = mapped_column(String(255))` and `ai_paused_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"))`.
- [ ] Implement AI pause on escalation: modify `app/domains/customer_service/services/suggested_actions.py:execute_action` escalate branch (line 891-920) to set `conversation.ai_paused = True` and `conversation.ai_paused_by_user_id = assigned_user_id` when escalation succeeds.
- [ ] Generate AI summary on escalation: in escalate action handler (suggested_actions.py), before marking conversation paused, call a new method `_generate_escalation_summary(conversation_id)` (to be implemented) that extracts last N messages, conversation context (customer, order info), and tags, then stores it in a new `EscalationContext` table with fields: escalation_id (UUID), conversation_id, summary (text), ai_summary (text), attempted_actions (jsonb), recommended_next_action (text).
- [ ] Wire handoff settings into AI decision gate: in workflow execution (agent_runner.py or appropriate AI loop), before generating reply, check `if conversation.ai_paused and not user_override_reengagement: return {skip reply}`. This prevents AI from replying when human is in control.
- [ ] Add human control relinquishment API: in `app/api/products/customer_service/inbox.py`, add POST /{ticket_id}/resume-ai endpoint that (1) verifies human permission, (2) sets conversation.ai_paused = False, (3) logs the action, (4) returns a confirmation. Add test that verifies AI can reply again after relinquishment.
- [ ] Add test for handoff state transitions: in `tests/customer_service/chat/`, create `test_customer_service_handoff_state_transitions.py` with tests: (1) escalate action pauses AI, verify conversation.ai_paused=True; (2) AI refuses to reply while paused, verify no response generated; (3) human calls resume-ai, AI can reply again; (4) escalation context is accessible in GET /{ticket_id} response so human sees summary and AI recommendation.
- [ ] Add escalation audit log: in escalate action (suggested_actions.py), after setting ai_paused, add to ConversationTagService or new EscalationAuditLog table: {timestamp, conversation_id, escalated_by, escalated_reason, previous_status, human_assigned_to}. 
