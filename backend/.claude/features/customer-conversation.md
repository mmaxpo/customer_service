# Feature: Customer Conversation

## Spec
- **What it should do:** Reliable message history, communication controls, and context needed to resolve the customer's request, without leaving Tajeran.
- **Layer:** product
- **Likely location (guess — verify, I don't have your repo):** domains/customer_service/conversations (messages, attachments, drafts, internal notes)
- **Key entities:** Conversation, Message, Attachment, Internal Note, Message Delivery, Customer, AI Draft
- **Core rules to check against:** Incoming/outgoing messages distinguishable; internal notes never sent to customers; message history immutable after send (except permitted metadata); attachments securely handled; sending requires authorization; delivery status not confused with successful delivery

## Acceptance criteria (from the v1 spec's "DONE" list)
- Full history visible; incoming/outgoing messages, attachments, internal notes, drafts, edit-before-send all work
- Delivery state shown; no cross-tenant leakage
- Tests cover send/failure behavior

## Production success condition
> A human agent can conduct a complete customer conversation from Tajeran without losing message history or context.

## Audit Result
_Filled in by `/audit-feature customer-conversation`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- Conversation CRUD: create/list/get_detail/delete in repositories/conversations.py + conversations API (conversations.py:49-122)
- Message history: ConversationRepository.list_messages/get_detail loads full history with messages + relationships (conversations.py:302, 89-102)
- Incoming/outgoing distinction: SenderType enum with customer, agent, ai, system, internal_note (schemas/conversations.py:27-32)
- Internal notes: InternalNoteService.add_note creates sender_type=INTERNAL_NOTE messages, marked internal=True in meta (services/internal_notes.py:21-54)
- Message delivery status: get_message_by_source_identity for idempotent replay detection, _reply_result tracks idempotent_replay flag (repositories/conversations.py:333, services/messaging.py:163-167)
- Drafts: CustomerServiceReplyDraft model (models/commercial.py:cs_reply_drafts), draft API endpoints in helpdesk.py (create/list/update/delete/schedule)
- Message immutability: no edit/update endpoints after send, messages only support metadata updates (update_message_meta)
- Tenant isolation: enforced via user_id/workspace_id in repos (get_for_user, get_detail)
- Tests: conversation_message_ownership.py, conversation_customer_ownership.py, message_source_identity.py, pagination tests

**Is it good enough?**
Mostly. Core workflow (create → message history → send/draft → deliver) is solid with good isolation. Strengths:
- Internal notes properly protected from customer exposure
- Idempotency via source_message_id prevents duplicate sends
- Drafts support edit-before-send with schedule capability
- Message immutability correct (append-only history)

Gaps:
- Attachments mentioned in spec but not in API schema (no dedicated attachment endpoints)
- Delivery status not exposed in ConversationMessage response (sync vs async delivery state unclear)
- No explicit conversation merge/split operations (merged_into_id field exists but no endpoint)

**Gaps / risks:**
1. Missing attachment API: spec lists Attachment as key entity; conversations.py has no /attachments endpoints
2. Delivery status not visible in API: omnichannel.py has delivery_status tracking but not returned in ConversationDetail
3. Message source identity edge case: ConversationMessageCreate requires source_type and source_message_id together, but API validation happens late (schema validation after instantiation)
4. No conversation merge endpoint: merged_into_id field exists in model but no API to merge/redirect conversations
5. Attachment security: if attachments exist, no evidence of access control or virus scanning

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add attachment schema and API: create AttachmentUpload and AttachmentRead schemas in schemas/conversations.py; add POST /conversations/{conversation_id}/attachments to upload and GET to list
- [ ] Include delivery status in ConversationMessage: add delivery_status: str | None field to ConversationDetailMessage schema; populate from external_message_link delivery tracking in repositories/conversations.py
- [ ] Add conversation merge endpoint: POST /conversations/{conversation_id}/merge in conversations.py that updates merged_into_id and redirects future messages
- [ ] Move source identity validation earlier: change ConversationMessageCreate.validate_source_identity from after-mode to before-mode to catch errors before message creation
- [ ] Add tests for attachment handling: test_customer_service_conversation_attachments.py covering upload/list/access control/cross-tenant leakage
- [ ] Add tests for delivery status flow: test_customer_service_message_delivery_status.py covering sync/async delivery, status updates from omnichannel webhooks
- [ ] Add tests for message immutability: test_customer_service_message_immutability.py verifying messages cannot be edited after send (only metadata)
- [ ] Add test for conversation merge: test_customer_service_conversation_merge.py covering merge semantics and message routing 
