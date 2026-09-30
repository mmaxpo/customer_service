# Feature: Basic SLA

## Spec
- **What it should do:** Track response and resolution commitments and warn/escalate when approaching or exceeding limits, respecting business hours/timezones.
- **Layer:** product
- **Likely location (guess — verify, I don't have your repo):** domains/customer_service/sla
- **Key entities:** SLA Policy, SLA Timer, Business Calendar, SLA Event, SLA Breach
- **Core rules to check against:** Business hours respected; timer behavior deterministic; response and resolution SLA separate; resolution stops the appropriate timer; SLA state survives system restart

## Acceptance criteria (from the v1 spec's "DONE" list)
- Business hours, first-response SLA, resolution SLA, timers, warnings, breaches, escalation all work
- Timezones handled correctly; tests cover boundary cases

## Production success condition
> Merchant can reliably see which conversations are approaching or exceeding their support commitments.

## Audit Result
_Filled in by `/audit-feature basic-sla`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- SLA Policy model: SLAPolicy (models/sla.py:35+) with first_response_minutes, resolution_minutes, business_hours (JSON), calendar_id, is_active, priority-scoped
- SLA Violation model: SLAViolation (models/sla.py:71+) with target_type (FIRST_RESPONSE/RESOLUTION), due_at, breached_at, status (enum: on_track, at_risk, breached)
- Business hours calculation: add_business_minutes() (services/sla.py:30-103) with timezone support, weekly windows, holiday handling
- SLA Calendar model: CustomerServiceSLACalendar for business hours templates with timezone, weekly_hours, holidays
- SLA Service: SLAService with policy management, target creation, breach detection (services/sla.py:106+)
- Automatic target creation: create_targets_for_ticket() creates FIRST_RESPONSE and RESOLUTION targets when ticket created
- Target resolution: resolve_first_response_targets() and resolve_resolution_targets() when messages received
- Breach detection: check_breaches() checks all SLA violations for breaches (services/sla.py:241+)
- At-risk detection: check_at_risk() identifies at-risk SLAs (services/sla.py:199+)
- API endpoints: POST/GET /sla/policies, GET /sla/violations, POST /sla/check, POST /sla/check-risk (workforce.py)
- SLA calendars API: POST/GET /sla/calendars, GET /sla/calendars/{id}/due-at (commercial.py)
- Tenant isolation: user_id scoped throughout
- Tests: comprehensive including business hours, breach detection, first response, resolution, idempotency, tenant isolation

**Is it good enough?**
Mostly. Strengths:
- Business hours calculation correct with timezone/holiday support
- First response and resolution SLAs separate
- Deterministic timer calculation with business hour windows
- State persisted across restarts (SLAViolation records durable)
- Idempotency tested
- Comprehensive test coverage

Gaps vs spec:
- Warning/escalation not wired: check_at_risk() exists but no automatic notification on approach to breach
- No escalation on breach: breach status detected but no automatic escalation/queue routing
- No dashboard metrics: list_violations exists but no aggregation/dashboard data
- No policy scheduling: policies based on priority, not time-based activation
- SLA history not exposed: violations records kept but no API to fetch SLA history for audit
- No bulk SLA application: policy per priority, no way to apply to multiple tickets at once
- Realtime publisher unused: defined but check_at_risk() doesn't publish warnings

**Gaps / risks:**
1. Warning notifications missing: check_at_risk() computes but doesn't notify approaching breaches
2. No automatic escalation: breaches detected but not escalated to queue/management
3. No dashboard/metrics API: only raw violation list, no SLA compliance metrics
4. Policy application limited: per-priority only, no channel/intent-based rules
5. No breach notification wired: status updated but agents not notified of breaches
6. SLA history not queryable: violations kept but no history export/audit trail

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Wire at-risk notifications: modify check_at_risk() in services/sla.py to call CustomerServiceRealtimePublisher.publish_sla_at_risk() + NotificationService.create()
- [ ] Add breach escalation: add escalation logic in check_breaches() to route breached tickets to escalation queue or assign to manager
- [ ] Add SLA metrics API: create GET /sla/metrics endpoint returning {breached: count, at_risk: count, on_track: count} by priority/channel
- [ ] Wire breach notifications: in check_breaches(), notify ticket assignee of breach via NotificationService
- [ ] Add SLA history API: add GET /tickets/{id}/sla-history endpoint returning all SLAViolation records for that ticket
- [ ] Add policy channel/intent rules: extend SLAPolicy to include channel and intent filters (models/sla.py)
- [ ] Add bulk SLA check job: create scheduled job (cron) to run check_breaches() and check_at_risk() periodically
- [ ] Add SLA policy update endpoint: PATCH /sla/policies/{id} to update thresholds, business hours, active status
- [ ] Add tests for breach escalation: test_customer_service_sla_breach_escalation.py covering automatic queue routing
- [ ] Add tests for at-risk notifications: test_customer_service_sla_at_risk_notification.py verifying notifications sent on approach 
