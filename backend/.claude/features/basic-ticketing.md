# Feature: Basic Ticketing

## Spec
- **What it should do:** Agents can create and manage a basic ticket (status, priority, assignee, team) linked to a conversation.
- **Layer:** product
- **Likely location (guess — verify, I don't have your repo):** domains/customer_service/tickets
- **Key entities:** Ticket, Conversation, Customer, Assignment, Team, Priority, Ticket Status
- **Core rules to check against:** Ticket belongs to workspace; can reference conversation; status changes auditable; resolution does not delete history; reopening preserves history

## Acceptance criteria (from the v1 spec's "DONE" list)
- Ticket creation, linking, status, priority, assignment, team, resolve, reopen, audit history all work

## Production success condition
> Agents can explicitly track customer issues as tickets without creating a second disconnected support system.

## Audit Result
_Filled in by `/audit-feature basic-ticketing`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- Ticket model: Ticket (models/tickets.py:39+) with status (TicketStatus enum), priority (TicketPriority enum), assigned_to, workspace_id, conversation_id, created_at, updated_at
- Auto-creation: tickets created automatically when conversation created (inbox/service.py:142-149, confirmed in tests)
- CRUD operations: TicketRepository with list, get, create, update methods (repositories/tickets.py)
- Status changes: PATCH /tickets/{id} + dedicated endpoints POST /tickets/{id}/close and /reopen (inbox.py:119-171)
- Priority & assignment: updatable via PATCH endpoint with TicketUpdate schema (schemas/tickets.py)
- Audit logging: CustomerServiceAuditLog model (models/tickets.py:160+) for tracking changes
- Tenant isolation: workspace_id scoped, user_id checks throughout
- History preservation: closed/resolved tickets not deleted; reopen restores state (inbox.py:156-171)
- Assignment tracking: TicketAssignment model (models/tickets.py:81+) links ticket to assignee with audit trail
- Tests: test_customer_service_ticket_lifecycle.py covers close/reopen/update, validation tests

**Is it good enough?**
Mostly. Strengths:
- Ticket ↔ Conversation linking solid
- Status/priority/assignee management working
- Audit logging in place
- History preserved on reopen
- Tenant isolation correct
- Comprehensive CRUD operations

Gaps vs spec:
- Team assignment not on Ticket model: spec requires "team" but handled via routing_policies (indirect)
- Status change audit not tested: CustomerServiceAuditLog exists but no test verifying status changes logged
- Reopen history preservation not explicitly tested: reopen works but no test confirming historical data retained
- No explicit team management: teams managed separately via routing, not directly assignable to ticket
- Ticket comments/internal notes missing: ticket changes tracked but no ticket-specific note system

**Gaps / risks:**
1. Team assignment incomplete: Ticket model lacks team_id field; team assignment done via routing not direct ticket assignment
2. Status change audit untested: AuditLog model exists but no test verifying status changes create audit entries
3. Reopen history not tested: reopen endpoint works but no test confirming conversation messages preserved
4. No ticket-scoped notes: ticket history only via conversation messages, no dedicated ticket notes
5. Assignment via string not UUID: assigned_to is String(255), not UUID foreign key to user table

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add team_id to Ticket model: add team_id: Mapped[UUID | None] field to Ticket (models/tickets.py:39+); add migration
- [ ] Create ticket status change audit: in TicketRepository.update(), call AuditLogRepository to log status changes (repositories/tickets.py)
- [ ] Add status change audit test: test_customer_service_ticket_status_audit.py verifying each status change creates audit log entry
- [ ] Add reopen history test: test_customer_service_ticket_reopen_preserves_history.py verifying conversation messages retained on reopen
- [ ] Fix assigned_to type: change assigned_to from String(255) to UUID with FK to user table (models/tickets.py:66)
- [ ] Add direct team assignment endpoint: POST /tickets/{id}/assign-team in inbox.py for direct team assignment
- [ ] Add ticket notes system: create TicketNote model (models/tickets.py) for ticket-scoped internal notes separate from conversation
- [ ] Add team management test: test_customer_service_ticket_team_assignment.py covering direct team assignment and routing
- [ ] Add audit log visibility: GET /tickets/{id}/audit-history endpoint returning status/priority/assignment changes
- [ ] Add bulk update support: PATCH /tickets?ids=[] for updating multiple tickets status/priority/assignment 
