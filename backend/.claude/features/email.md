# Feature: Email Channel

## Spec
- **What it should do:** Incoming support emails become conversations, and Tajeran can send replies while preserving threading and attachments.
- **Layer:** product
- **Likely location (guess — verify, I don't have your repo):** domains/customer_service/channels/email
- **Key entities:** Email Channel, Email Account, Email Message, Conversation, Thread, Attachment, Customer Identity
- **Core rules to check against:** Email thread maps correctly to conversation; incoming email tenant-scoped; attachments secure; outgoing messages use correct merchant identity; duplicate delivery handled safely

## Acceptance criteria (from the v1 spec's "DONE" list)
- Inbound email received and becomes conversations; threads preserved
- AI and human can respond; attachments work
- Customer identity resolved; delivery state tracked; tenant isolation works

## Production success condition
> A real merchant can operate their support email from Tajeran's unified inbox.

## Audit Result
_Filled in by `/audit-feature email`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- Inbound email ingestion: NormalizedInboundEmail schema (inbox/schemas.py:23-44), InboundEmailIngestService (inbox/service.py:34-202), POST /email/ingest endpoint
- Email thread resolution: EmailThreadingResolver (inbox/threading.py) with 3 strategies: external_thread_id, in_reply_to/references headers, subject+customer matching
- Customer identity matching: calls CustomerIdentityService.resolve_existing() in ingest (inbox/service.py:74-77)
- Duplicate delivery prevention: PostgreSQL advisory lock + external_message_id lookup prevents re-ingestion (inbox/service.py:46-72)
- Thread preservation: email metadata (external_thread_id, in_reply_to, references, subject, from/to/cc/bcc) stored in ConversationMessage.meta (inbox/service.py:114-135)
- Attachment handling: attachments metadata stored in message.meta with filename, content_type, url, provider_attachment_id (inbox/schemas.py:14-20)
- Outbound reply: send_reply() in CustomerServiceMessagingService calls send_email() (services/messaging.py:44, :130)
- Resend webhook: POST /email/webhooks/resend/{workspace_id} ingests delivery events (inbox.py:55-70)
- Conversation auto-creation: new thread creates Conversation + Ticket (inbox/service.py:105-149)
- Tenant isolation: user_id scoped queries throughout (inbox/service.py, threading.py)
- Tests: thread isolation, idempotency, identity resolution, basic inbox flow (test_customer_service_inbox_email*.py)

**Is it good enough?**
Mostly. Strengths:
- Thread preservation via multiple strategies (ID, headers, subject)
- Duplicate delivery handled safely
- Identity resolution integrated
- Tenant isolation correct
- Inbound → conversation pipeline works end-to-end

Gaps vs spec:
- Email account configuration missing: no UI/API to connect merchant email account (accept inbound but no outbound config)
- Outbound email sender verification missing: no check that agent has permission to send from merchant email
- Delivery status not visible in API: Resend webhook ingests but status changes not exposed
- Reply-to headers not set: outbound email should include In-Reply-To and References for client-side threading
- Attachment storage incomplete: only metadata stored, not actual files
- No conversation assignment to agent (created ticket but no assignment flow shown)
- Manual agent reply not tested (only outbound.send_email but no agent→customer flow test)

**Gaps / risks:**
1. Missing merchant email account config: spec requires "support email operated from Tajeran" but no account setup/SMTP configuration
2. Reply-to headers missing: outbound messages don't set In-Reply-To/References for proper client threading
3. Outbound sender verification missing: no check that user can send from merchant email address
4. Delivery status not exposed: Resend webhook received but events not returned via API
5. No attachment file storage: only URL/metadata kept; actual files not persisted
6. Merchant identity not configurable: who can send from what address not controlled

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add email account configuration: create EmailAccount model (models/email.py) with smtp_host, smtp_port, username, password, verified_domain; add API endpoints (create/list/delete)
- [ ] Add outbound reply headers: modify send_reply() in services/messaging.py to set In-Reply-To and References headers from message.meta before calling send_email()
- [ ] Add sender verification: in send_reply(), verify current_user can send from merchant email account (check EmailAccount.verified_domain matches reply-to domain)
- [ ] Expose delivery status: add GET /conversations/{id}/delivery-status endpoint returning list of delivery events from Resend webhook ingestion
- [ ] Add attachment file storage: store attachment files in object storage (S3/GCS); modify InboundEmailIngestService to fetch and persist files
- [ ] Add agent reply test: test_customer_service_email_agent_reply.py covering agent sends reply → customer receives email with proper headers
- [ ] Add conversation assignment on ingest: in inbox/service.py, auto-assign created ticket to routing queue or first available agent
- [ ] Add email headers to outbound: include X-Priority, X-MSMail-Priority from ticket priority for email client visibility
- [ ] Add rate limiting: implement rate limiter in POST /email/ingest endpoint (max 100 emails/minute per account_id)
- [ ] Add resend provider setup docs: create docs/EMAIL_SETUP.md with Resend API key configuration, webhook setup, DNS verification 
