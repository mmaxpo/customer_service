# Release 2 backend handoff

Release 2 turns the customer-service domain into a workspace-scoped commercial
support backend. The database head is `cap041`; deploy migrations before API and
worker processes.

## Merchant product contract

All authenticated customer-service requests must include `X-Workspace-ID`.
Roles are owner, admin, agent, and viewer. The frontend should treat 402 as an
inactive/missing entitlement, 409 as an edit/idempotency conflict, and 429 as a
quota or abuse limit.

The sellable inbox contract now includes:

- verified Resend inbound email and idempotent outbound email/website replies;
- search, filters, shared/private saved views, collision leases, attachments,
  malware scanning, assignments, mentions, approval and SLA notifications;
- business calendars, holidays, SLA risk/breach checks and escalation metadata;
- customer/conversation merge, conversation split, resolution outcomes and CSAT;
- onboarding status, idempotent demo data and provider-health reporting;
- trials, plans, signed billing lifecycle changes and enforced conversation and
  feature entitlements;
- consent recording, auditable export/anonymization jobs and retention preview;
- workspace-scoped workflow approvals, timeline, snapshots and replay;
- workspace-scoped customer-service realtime via
  `GET /realtime/stream?scope=customer_service&workspace_id=<uuid>`.
- merchant autopilot policy, unified automation activity and structured
  multilingual intelligence with deterministic fallback;
- snooze/follow-up jobs, spam/phishing quarantine, bulk actions, durable drafts,
  server-side reply signatures, custom customer fields and agent productivity;
- business-value analytics and six configurable proactive playbooks with durable
  incidents, cooldown deduplication and worker evaluation.

OpenAPI is the source of truth for request/response fields. Frontend navigation
should be organized around these groups:

1. Inbox: `/customer-service/inbox`, `/search`, conversations, tickets, presence,
   attachments and saved views.
2. Automation: workflow templates/executions, `/workflow-approvals`, suggested
   actions, event subscriptions and objective learning.
3. Operations: agents, teams, queues, routing, SLA calendars/policies,
   notifications, analytics and audit logs.
4. Settings: onboarding, provider health, Shopify, subscription and privacy.

## Agentic core exposed to the product

The customer-service layer already uses the reusable core for durable jobs,
events, retries/dead letters, human approvals, waits/resume, workflow templates,
snapshots/replay/timeline, capabilities/provider health, objective interpretation,
clarification, guarded Shopify execution, outcome verification, repair planning,
and learning from resolved outcomes. Public website chat runs the support
objective orchestration path; verified inbound email now triggers suggested
actions and event-based workflows without rejecting accepted email when an
optional AI follow-up fails.

The backend product increments above now use these core capabilities rather than
parallel domain runtimes. Additional providers remain deliberately hidden until
their production implementations pass the same lifecycle and smoke-test gates.

## Production configuration and release gate

Required merchant integrations must be configured before onboarding a paying
store: Shopify credentials/scopes/encryption key, Resend API and webhook secret,
Redis, CORS origins, email sender domains, Sentry, backup destination and billing
webhook secret. Use a durable attachment volume. `clamdscan` mode fails closed
and therefore also requires the scanner binary/daemon in the deployment image;
the default built-in mode blocks executables and known test signatures but is not
a substitute for a managed malware scanner at scale.

Billing is intentionally provider-neutral in this release. Only a verified,
timestamped billing webhook can change plans or entitlements. Before charging
real stores, choose Shopify App Billing, Stripe, or another processor and connect
its hosted checkout/customer portal to this signed lifecycle boundary. Do not
add an authenticated endpoint that directly grants its own entitlements.

The in-process realtime hub supports one API replica. Before horizontal API
scaling, replace its delivery transport with Redis Pub/Sub or Streams while
keeping the existing event schema and SSE contract.

Release verification:

```bash
python scripts/check_migrations.py
pytest -q
docker build -f infra/Dockerfile -t tajeran-backend:release2 .
docker compose -f infra/docker-compose.prod.yml config
```

The migration checker creates an isolated database, upgrades empty-to-head,
downgrades the latest schema-only revision, upgrades again, verifies `cap041`,
and removes the database. Production rollback must never cross the forward-only
workspace ownership cutover at `cap034`; restore a verified backup into a new
database instead.

The worker health probe now checks both PostgreSQL and a fresh worker-loop
heartbeat. PostgreSQL, Redis and attachment data all require independent,
encrypted, off-site backups and periodic restore drills.
