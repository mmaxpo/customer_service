# Feature: Website Chat + Channel Abstraction

## Spec
- **What it should do:** Customer-facing website chat channel whose conversations enter the same unified conversation model used by email and future channels.
- **Layer:** product
- **Likely location (guess — verify, I don't have your repo):** domains/customer_service/channels/webchat + channel abstraction layer
- **Key entities:** Channel, Channel Connection, Conversation, Customer Identity, Message, Channel Session
- **Core rules to check against:** Channel-specific details must not contaminate the core conversation model; customer identity handled safely; messages retain channel metadata; future channels should reuse the same abstraction

## Acceptance criteria (from the v1 spec's "DONE" list)
- Widget installs and opens; customer can send message; conversation created
- AI and human can respond; handoff works
- Customer identification and basic customization work
- Channel abstraction preserved

## Production success condition
> A real Shopify customer can open the widget, communicate with Tajeran, and have the conversation handled through the same core support system.

## Audit Result
_Filled in by `/audit-feature website-chat-channel`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- Widget settings model: CustomerChatWidgetSettings (models/chat.py:37-111) with public_key, title, welcome_message, brand_color, position, auto_answer config
- Chat sessions: CustomerChatSession model (models/chat.py:114-179) tracking visitor_id, customer email/name, channel, status
- Chat messages: CustomerChatMessage (models/chat.py:236-291) with client_message_id for idempotency, linked to session
- Inbox bridge: CustomerChatInboxLink (models/chat.py:182-233) linking chat_session → customer → conversation → ticket
- Public widget API: unauthenticated endpoints using public_key for create_session, create_message, list_messages (channels.py:247-503)
- Widget customization API: GET/PUT /customer-service/chat/widget/settings for merchant configuration (channels.py:173-216)
- Chat service: CustomerChatService handles session/message creation, widget settings, inbox bridging (services/chat_service.py)
- Auto-reply workflow: chat messages trigger workflows (e.g., "customer.chat.message.created" event) tested in test_customer_service_chat_workflow_auto_reply_e2e.py
- Inbox integration: chat messages create conversations, visible in inbox with channel="website" (test_customer_service_chat_inbox_bridge.py)
- Channel abstraction layer: omnichannel models for external channel connections (models/omnichannel.py, though not used for website chat yet)
- Idempotency: client_message_id unique index prevents duplicate chat messages (models/chat.py:240-248)
- Tests: widget CRUD, public session flow, auto-reply E2E, inbox bridge, manual reply, automation settings

**Is it good enough?**
Mostly complete. Strengths:
- Widget installation via public_key — no auth needed
- Customers can send messages → creates conversation in unified model
- AI replies via event subscription workflows work
- Inbox bridge ties chat to core conversation model
- Customization supports basic branding

Gaps vs spec:
- Handoff (human escalation) not explicitly tested — auto-reply works but no dedicated "escalate to human" endpoint/workflow
- Customer identification incomplete: email/name captured in chat session but not linked to customer identity service (CustomerIdentityService exists but not called)
- Widget SDK missing: only REST API endpoints exist; no JavaScript widget code in repo
- Channel metadata not retained: messages lose channel-specific context after inbox bridge
- No message sequence/ordering guarantees across chat + inbox views
- Session lifecycle not managed: no timeout, close, or explicit handoff state

**Gaps / risks:**
1. Handoff workflow missing: spec requires "handoff works" but no test or dedicated escalate endpoint
2. Customer identity resolution incomplete: chat captures email but doesn't resolve to customer record via identity service
3. No JavaScript widget SDK: backend API exists but frontend widget not in repo (externally managed?)
4. Channel metadata lost in transition: message goes from CustomerChatMessage to ConversationMessage, channel metadata (e.g., "customer_chat") not preserved in conversation view
5. Session state incomplete: no explicit handoff_to/handoff_status field; no timeout management
6. No message ordering guarantee: chat and inbox might show messages in different order
7. Spam/rate limiting missing: no protection against customer flooding widget with messages
8. Manual agent reply not well-tested: only automated workflows tested, not agent → customer via chat widget

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add handoff endpoint: POST /customer-service/chat/sessions/{session_id}/escalate in channels.py that marks session for human handoff and creates workflow job
- [ ] Wire customer identity resolution: call CustomerIdentityService.resolve_existing() in CustomerChatService.ensure_inbox_bridge_for_session() to match chat session to customer record
- [ ] Add session lifecycle management: add handoff_to_user_id and status fields to CustomerChatSession model; add session close endpoint
- [ ] Preserve channel metadata: add channel source tracking to ConversationMessage.meta when bridging chat to inbox (already done via source="customer_chat")
- [ ] Add message ordering: extend GET /conversations/{id}/messages to accept order_by parameter and ensure consistent ordering across chat + conversation views
- [ ] Add rate limiting: implement rate limiter in create_message endpoint (max 10 messages/minute per visitor_id)
- [ ] Add tests for human handoff: test_customer_service_chat_human_handoff.py covering escalate → inbox notification → agent reply → chat display
- [ ] Add tests for agent reply to chat: test_customer_service_chat_agent_reply.py verifying agent response in inbox appears back in chat widget
- [ ] Add widget documentation: create docs/WEBSITE_CHAT_INTEGRATION.md with public_key usage, session creation, message flow examples
- [ ] Add session timeout: add idle_timeout_minutes to CustomerChatWidgetSettings; implement cleanup job to close stale sessions 
