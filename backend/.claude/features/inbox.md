# Feature: Inbox

## Spec
- **What it should do:** One place for agents to see, search, filter, prioritize, assign, and resolve customer conversations.
- **Layer:** product
- **Likely location (guess — verify, I don't have your repo):** domains/customer_service/inbox
- **Key entities:** Conversation, Conversation Assignment, Team, User, Tag, Conversation Status, Priority, Channel
- **Core rules to check against:** Conversation belongs to exactly one workspace; assignment references valid workspace members; agents only access authorized conversations; closing/reopening preserves history; AI vs human handling state distinguishable

## Acceptance criteria (from the v1 spec's "DONE" list)
- List, search, filter, assign/reassign all work
- Status, priority, tags work
- Snooze, close/reopen, escalate work
- AI/human states visible; tenant isolation works
- Tests cover core operations

## Production success condition
> A support agent can operate their daily customer-service workload entirely from the Tajeran inbox.

## Audit Result
_Filled in by `/audit-feature inbox`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- Inbox listing with folder filtering (inbox/snoozed/spam/all): `app/domains/customer_service/repositories/inbox.py` + `app/api/products/customer_service/inbox.py`
- Ticket CRUD: list, get, update, close, reopen in tickets API endpoints (inbox.py:98-171)
- Assignment: `AssignmentService` with notification (services/assignment.py), endpoint at inbox.py:174-190
- Tags: database model ConversationTag, service methods (add_tag/list_tags/remove_tag), API endpoints in conversations.py
- Status/Priority: stored in Ticket model, visible in TicketRead schema, updatable via PATCH endpoint
- Snooze: model field snoozed_until (models/core.py:222-228), API endpoint in helpdesk.py (snooze_conversation)
- Close/Reopen: dedicated endpoints inbox.py:138-171
- AI/Human state: visible via sender_type in ConversationMessage model (models/core.py:242+)
- Tenant isolation: enforced via user_id checks in InboxRepository.list() and other methods
- Tests: test_customer_service_ticket_lifecycle.py, test_customer_service_tickets.py cover basic CRUD + close/reopen

**Is it good enough?**
Partially. Core workflow (list → assign → work → close) is solid with tests. However:
- Escalate missing: exists as SuggestedAction type but no dedicated endpoint to move ticket to escalation queue/team
- Filter/search incomplete: search_conversations in commercial.py is separate; can't filter inbox by tags, no composite filter (e.g., status=open + priority=high + tags=[urgent])
- Snooze/tags tested via manual paths, not via inbox test suite
- No dedicated reassign endpoint; reassignment only via ticket PATCH
- Conversation tags not returned in InboxItem schema, so agents can't see tags in list view

**Gaps / risks:**
1. Escalate endpoint missing — agents can't escalate from inbox UI
2. Tags not in InboxItem response — agents must fetch tags separately per item
3. Search/filter not accessible through inbox endpoints — search is in commercial.py, not product layer
4. Missing tests for snooze, tag operations, filter combinations
5. No API for bulk operations (close multiple, tag multiple)

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add escalate endpoint: POST /tickets/{ticket_id}/escalate in inbox.py that moves ticket to escalation queue (requires queue assignment logic)
- [ ] Include tags in InboxItem response: add tags: list[str] field to inbox.py InboxItem schema and populate from ConversationTag in InboxRepository.list()
- [ ] Expose search via inbox router: add GET /inbox/search endpoint in inbox.py that wraps search_conversations from commercial.py
- [ ] Add filter parameters to inbox: extend GET /inbox to accept optional filters (status, priority, tags) and pass to InboxRepository.list()
- [ ] Add dedicated reassign endpoint: POST /tickets/{ticket_id}/reassign in inbox.py (wrapper around assign with audit logging)
- [ ] Add tests for snooze lifecycle: test_customer_service_inbox_snooze.py covering snooze/unsnooze/list with snooze filtering
- [ ] Add tests for tag operations in inbox context: test_customer_service_inbox_tags.py covering add/remove/list tags + filter inbox by tags
- [ ] Add tests for search: test_customer_service_inbox_search.py covering search query parameter in get_inbox endpoint 
