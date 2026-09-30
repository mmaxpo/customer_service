# Tajeran Backend Updated Analysis: Tests, Migrations, and Infra

## Uploaded Archive Reviewed

Archive reviewed: `Archive(4).zip`

Detected contents:

- `tests/`
- `migrations/`
- `infra/`

This archive completes the missing backend contract layer. The previous backend upload showed the application architecture. This upload shows how that architecture is tested, persisted, and prepared for development infrastructure.

---

## Quantitative Summary

| Area | Count |
|---|---:|
| Total extracted files, excluding macOS metadata | 489 |
| Python test files | 183 |
| Detected test functions | 316 |
| Customer-service test files | 103 |
| Platform/root test files | 80 |
| Alembic migration version files | 50 |
| Persisted tables detected from migrations | 53 |
| Infra files | Dockerfile, docker-compose.dev.yml, SearXNG settings |

---

## What the Tests Prove

The tests confirm that Tajeran is not a normal CRUD backend. It is a platform backend with a first product built on top of it.

The first product is an AI-native, Shopify-first customer-service/helpdesk system.

The reusable platform includes workflow runtime, agent runtime, event bus, jobs, schedules, webhooks, workflow waits, snapshots, versions, quality, evaluations, metrics, and deployments.

---

# 1. Customer Service Product Test Coverage

The customer-service domain has the strongest test coverage in the archive.

Detected test files: **103**

## Customer-Service Areas Covered

### Core Support Objects

Test coverage confirms:

- Customers
- Conversations
- Conversation messages
- Tickets
- Ticket lifecycle
- Ticket assignment
- Tags
- SLA policies
- SLA violations
- Timelines
- Audit logs
- Internal notes
- Macros
- Inbox email flow

### AI / Agent Assist

Test coverage confirms:

- AI reply generation
- AI reply regeneration
- AI reply metadata
- Reply quality metadata flow
- Agent assist lifecycle
- Agent assist list endpoint
- Agent assist timeline events
- Agent assist suggestions
- Suggestion approval
- Suggestion rejection
- Suggestion send flow
- Suggestion revisions

### Suggested Actions

Test coverage confirms:

- Suggested action lifecycle
- Suggested action execution
- Knowledge fail-soft behavior
- Shopify suggested actions
- Prepared workflow-backed suggested actions
- Finishers and action completion behavior

### Conversation Intelligence

Test coverage confirms:

- Conversation triage
- Conversation analytics
- Conversation insights
- Intent / priority / tag classification
- Phase 1 triage, analytics, and SLA behavior
- Phase 2 conversation intelligence behavior

### Quality

Test coverage confirms:

- Quality reviews
- Reply quality dashboard
- Reply quality insights
- Reply quality insight buckets
- AI reply metadata to quality review flow

### Routing / Workforce

Test coverage confirms:

- Agents
- Agent capacity
- Best-agent selector
- Agent capacity routing
- Unavailable-agent routing guards
- Routing policies
- Routing auto-assignment
- Team security and membership
- Team policy best-agent routing
- Queues
- Queue/team routing
- Permission denied guards
- Concurrency guards

### Shopify

Test coverage confirms:

- Shopify connection
- Shopify OAuth callback skeleton
- Shopify order context
- Shopify order cache
- Shopify support orchestrator
- Shopify workflow decisions
- Shopify workflow templates
- Shopify event subscription seeding
- Shopify event to workflow job
- Shopify suggested actions
- Shopify prepared support workflow API
- Refund/cancel/shipping-status/change-address/damaged-item decision handling

Important product implication:

The backend already encodes business rules for support workflows, not just integration plumbing.

### Shipping

Test coverage confirms:

- Shipping tracking
- Shipping cache
- Phase 3 shipping behavior

### Knowledge

Test coverage confirms:

- Customer-service knowledge endpoints/services
- Knowledge-backed suggested replies
- Knowledge fail-soft behavior

---

# 2. Omnichannel Test Coverage

Omnichannel has deep and important coverage.

## Covered Areas

Tests confirm:

- Omnichannel inbound normalization
- Omnichannel outbound sending
- Outbound enqueue API
- Outbound delivery job
- Outbound worker behavior
- Permanent failure handling
- Delivery events
- Delivery history
- Platform event publishing
- Auto-routing after inbound messages
- Provider contract
- Provider capabilities
- Provider capabilities API
- Provider retry policy
- Provider retry behavior
- Webhook signature verification
- Webhook verification
- Webhook normalization
- Idempotency
- Channel connections

## Providers Covered

Tests confirm provider-specific behavior for:

- WhatsApp
- Instagram
- Generic provider abstraction

Product implication:

The omnichannel system is already built around a canonical internal model:

- External provider message comes in
- Webhook is verified
- Payload is normalized
- Internal conversation/message is created or linked
- Idempotency prevents duplicates
- Auto-routing may assign it
- Platform events/workflow jobs may be triggered
- Outbound replies can be enqueued and delivered through provider adapters

This is the correct long-term structure.

---

# 3. Workflow Runtime Test Coverage

The platform workflow runtime has broad coverage.

## Covered Runtime Capabilities

Tests confirm:

- Runtime node catalog
- Workflow validation
- Workflow execution
- Router node behavior
- Join node behavior
- Join/router skip behavior
- Deterministic join ordering
- Loop control
- Controlled cycle handling
- Timeouts
- Subworkflow execution
- Pause/resume
- Human approval endpoint flow
- Wait nodes
- Time waits
- Event waits
- Wait scheduler claims
- Resume concurrency
- SSE streams
- SSE no-replay behavior
- Run compare
- State diff
- Timeline/debugging
- Workflow metrics
- Workflow versions
- Workflow snapshots
- Workflow deployments
- Workflow evaluation datasets
- Workflow evaluation engine
- Workflow quality scoring
- Runtime persistence / Postgres integration

Product implication:

Tajeran’s workflow runtime is not only an execution helper. It is a durable orchestration engine.

This matters because customer service workflows can become durable business processes:

- refund approval
- damaged item investigation
- shipping delay escalation
- SLA breach escalation
- subscription-triggered workflows
- human-in-the-loop actions
- agentic support flows

---

# 4. Agent Runtime Test Coverage

Agent runtime tests confirm a separate agent execution subsystem.

## Covered Agent Runtime Capabilities

Tests confirm:

- Agent loop
- Tool execution
- Dangerous tool approval
- Unknown tool failure
- Max-step failure
- Usage tracking
- Budget enforcement
- State machine
- State persistence
- Event recording
- Event stream
- Event store
- Tool registry
- Built-in tools
- Custom workflow agent node
- Parent workflow run IDs
- Agent pause after approval
- Resume after approval
- Agent custom workflow composition
- Parallel agent joins
- Trace propagation

Product implication:

The backend supports workflow nodes that can run agents, pause for approval, resume safely, emit events, and enforce budget/tool constraints.

This is a major advantage over a normal support chatbot.

---

# 5. Jobs / Webhooks / Events / Integrations

## Jobs

Tests confirm:

- Platform jobs
- Job hardening
- Dead-letter queue
- Retry behavior
- Job heartbeat behavior
- Webhook-to-job handoff

## Webhooks

Tests confirm:

- Webhook endpoints
- Webhook deliveries
- Provider adapters
- Webhook normalization into jobs

## Platform Events

Tests confirm:

- Platform event storage
- Event publishing / listing behavior

## Integration Gateway

Tests confirm:

- Gateway success path
- Retry then success
- Timeout handling
- Circuit breaker opening

Product implication:

The backend is designed for real-world failure modes:

- external API failures
- webhook retries
- duplicate messages
- transient provider errors
- permanent provider errors
- async job processing
- DLQ recovery paths

---

# 6. Migrations Analysis

Detected Alembic version files: **50**

Detected persisted tables: **53**

## Platform Tables

Migrations define storage for:

- `user`
- `document`
- `thread`
- `message`
- `runtime_workflows`
- `workflow_runs`
- `workflow_run_events`
- `workflow_definitions`
- `workflow_versions`
- `workflow_waits`
- `workflow_run_snapshots`
- `workflow_run_metrics`
- `workflow_deployments`
- `workflow_eval_datasets`
- `workflow_eval_cases`
- `agent_runs`
- `agent_run_events`
- `platform_jobs`
- `platform_dead_letters`
- `platform_events`
- `webhook_endpoints`
- `webhook_deliveries`
- `workflow_schedules`

## Customer-Service Tables

Migrations define storage for:

- `cs_customers`
- `cs_conversations`
- `cs_conversation_messages`
- `cs_conversation_tags`
- `cs_tickets`
- `cs_ticket_assignments`
- `cs_sla_policies`
- `cs_sla_violations`
- `cs_audit_logs`
- `cs_macros`
- `cs_conversation_insights`
- `cs_suggested_actions`
- `cs_agent_assist_suggestions`
- `cs_agent_assist_suggestion_revisions`
- `cs_quality_reviews`
- `cs_shopify_connections`
- `cs_shopify_order_cache`
- `cs_shipping_tracking_cache`
- `cs_channel_connections`
- `cs_external_conversation_links`
- `cs_external_message_links`
- `cs_routing_policies`
- `cs_agents`
- `cs_teams`
- `cs_team_members`
- `cs_queues`
- `cs_event_subscriptions`
- `cs_workflow_templates`
- `cs_chat_sessions`
- `cs_chat_messages`

## Migration Graph Note

The migration graph mostly forms a connected chain, but the current detected head is:

- `eccd20e35ed0_add_customer_chat_models.py`

There are also merge migrations already present, including:

- `d2b505863121_merge_migration_heads.py`
- `f1b000000001_merge_customer_service_phase1_heads.py`

Development rule:

Any future model/schema change must come with a matching Alembic migration and focused migration test or API test where relevant.

---

# 7. Infra Analysis

## Dockerfile

The backend Dockerfile uses:

- Python 3.12 slim
- `uv`
- locked dependency install with `uv sync --frozen --no-dev`
- app served by Uvicorn through `app.main:app`

## Dev Compose

The dev compose file includes:

- PostgreSQL via `pgvector/pgvector:pg16`
- pgAdmin
- Frontend dev service
- Frontend connects to backend through `host.docker.internal:8000`

Product implication:

The backend is expected to use Postgres with pgvector capability, which fits the knowledge/RAG and hybrid search direction.

---

# 8. Updated Backend Understanding

After this test/migration archive, the correct mental model is:

## Tajeran Backend = Reusable AI Workflow Platform + Customer-Service Product

### Platform Layer

- Workflow engine
- Agent runtime
- Event bus
- Jobs
- Webhooks
- Schedules
- Waits
- Snapshots
- Versions
- Deployments
- Metrics
- Evaluations
- Quality scoring
- Integration gateway

### Product Layer

- Customer service/helpdesk
- Shopify support automation
- Omnichannel inbox
- Agent assist
- Suggested actions
- Workflow templates
- Event subscriptions
- Routing/teams/queues/agents
- SLA/tickets/tags/audit/macros
- Knowledge-backed replies
- Quality review and reply scoring

### Persistence Layer

- Alembic-managed Postgres schema
- pgvector-ready infrastructure
- Durable workflow/agent/job/customer-service state

---

# 9. Development Contract Going Forward

Before future backend changes:

1. Inspect the current code first.
2. Locate existing service/repository/router/model pattern.
3. Add changes inside the correct bounded context.
4. Add or update tests first where possible.
5. Add Alembic migrations for schema changes.
6. Run focused tests for the touched domain.
7. Then run broader tests.

## Preferred Future Patch Style

Because this backend is large and mature, changes should be delivered as small terminal patch steps:

1. One focused backend capability at a time.
2. One patch command at a time.
3. Include test command after each patch.
4. Avoid large all-in-one scripts.
5. Do not create parallel architecture when an existing module already owns the concept.

---

# 10. Important Product Conclusion

This archive confirms that Tajeran’s first product is already moving toward a strong market position:

> AI-native omnichannel customer service for Shopify merchants, powered by a reusable workflow/agent orchestration platform.

The backend has the right foundations for:

- Gorgias-like Shopify support
- Intercom-like inbox/conversations
- Zendesk-like tickets/SLA/routing
- AI agent assist
- Workflow automation
- Event-driven customer-service operations
- Human-in-the-loop support automation

The next important work should be careful frontend alignment and product UX, not rebuilding backend foundations.