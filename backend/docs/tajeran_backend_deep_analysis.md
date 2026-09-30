# Tajeran Backend Deep Analysis — Current Uploaded Backend

## Executive summary

The clean mental model is:

1. **Platform layer**: reusable orchestration/runtime infrastructure.
2. **Product/domain layer**: `app/domains/customer_service`.
3. **Integration layer**: omnichannel providers, Shopify, shipping, webhooks, knowledge, external tools.
4. **Operational layer**: jobs, schedules, waits, metrics, snapshots, timeline, quality, evaluations.

This means Tajeran is moving toward an AI-native customer-service operating system, not a simple helpdesk.

---

## Repository scale observed

Important code areas found in the uploaded archive:

| Area | Python files | Approx lines | Meaning |
|---|---:|---:|---|
| `app/domains/customer_service` | 182 | ~15,789 | Main product domain |
| `app/runtime` | 67 | ~8,093 | Workflow DAG/runtime engine |
| `app/agents_runtime` | 43 | ~1,856 | Agent runtime and tool execution |
| `app/jobs` | 15 | ~991 | Async job queue / retries / DLQ |
| `app/platform/events` | 11 | ~417 | Platform event bus/store/handlers |
| `app/webhooks` | 11 | ~433 | Generic webhook framework |
| `app/workflow_versions` | 5 | ~549 | Workflow definition/version lifecycle |
| `app/workflow_snapshots` | 7 | ~257 | Snapshot/replay layer |
| `app/workflow_timeline` | 3 | ~135 | Run timeline/debugging surface |
| `app/workflow_quality` | 4 | ~179 | Workflow quality scoring/gates |
| `app/workflow_metrics` | 4 | ~258 | Runtime metrics aggregation |
| `app/workflow_evaluations` | 8 | ~578 | Evaluation/regression support |
| `app/workflow_diff` | 5 | ~317 | Snapshot/run comparison |
| `app/workflow_deployments` | 5 | ~236 | Deployment management |
| `app/schedules` | 6 | ~419 | Scheduled execution foundation |

The archive did **not** include a `tests/` directory or migration folder. Existing tests and migrations should be added later before deep implementation changes.

---

## App composition

`app/main.py` creates the FastAPI app, configures CORS, attaches tools to request state, registers builtin runtime nodes, initializes workflow repo, initializes agent runtime services, and wires routers.

Included platform routers:

- Auth
- Knowledge endpoints
- Runtime workflows
- Agent runtime
- Tool catalog
- Jobs
- Schedules
- Webhooks
- Platform events
- Workflow waits
- Workflow snapshots
- Workflow timeline
- Workflow diff
- Workflow evaluations
- Workflow versions
- Workflow metrics
- Workflow quality
- Resend email

Included product router:

- `app.domains.customer_service.main.router`

Important note: `customer_service_inbox_router` is included twice, once directly and once under `/customer-service/inbox`. This may be intentional for compatibility, but should be checked when tests are added to avoid duplicate route confusion.

---

## Customer-service product architecture

Customer-service routing is composed in `app/domains/customer_service/main.py` under prefix:

```text
/customer-service
```

It registers these domain modules:

- Inbox
- Conversations
- Customers
- Channels
- Workflows
- Analytics
- Tickets
- SLA
- Tags
- Audit logs
- Macros
- Conversation intelligence
- Suggested actions
- Reply quality
- Reply quality insights/dashboard/trends
- Quality reviews
- Workflow templates
- Workflow executions
- AI replies
- Knowledge
- Shopify
- Shipping
- Omnichannel
- Event subscriptions
- Routing policies
- Agents
- Teams
- Queues
- Chat
- Webhooks

This is a broad helpdesk domain already moving toward enterprise support operations.

---

## Customer-service domain model capabilities

Primary database models found in `app/domains/customer_service/models/models.py`:

### Core helpdesk
- `Customer`
- `Conversation`
- `ConversationMessage`
- `Ticket`
- `ConversationTag`
- `CustomerServiceAuditLog`
- `CustomerServiceMacro`

### Chat widget / customer live chat
- `CustomerChatSession`
- `CustomerChatMessage`

### Agent assist / AI reply lifecycle
- `AgentAssistSuggestion`
- `AgentAssistSuggestionRevision`
- `CustomerServiceQualityReview`
- reply quality fields on quality review records

### SLA
- `SLAPolicy`
- `SLAViolation`

### Assignment and routing
- `TicketAssignment`
- `CustomerServiceRoutingPolicy`
- `CustomerServiceAgent`
- `CustomerServiceTeam`
- `CustomerServiceQueue`
- `CustomerServiceTeamMember`

### Intelligence and actions
- `CustomerServiceConversationInsight`
- `CustomerServiceSuggestedAction`

### Workflows in product domain
- `CustomerServiceWorkflowTemplate`
- Event subscriptions connected to workflow templates / inline workflow JSON

### Shopify and shipping
- `CustomerServiceShopifyConnection`
- `CustomerServiceShopifyOrderCache`
- `CustomerServiceShippingTrackingCache`

### Omnichannel
- `CustomerServiceChannelConnection`
- `CustomerServiceExternalConversationLink`
- `CustomerServiceExternalMessageLink`
- `CustomerServiceEventSubscription`

Key design decision already visible: external omnichannel IDs are separated from internal conversation/message IDs through link tables. This is the right long-term design for WhatsApp/Instagram/email/chat/webhooks because it preserves internal canonical conversations while allowing provider-specific identity mapping.

---

## Customer-service API surface observed

### Conversation and inbox
- Create/list conversations
- Conversation detail
- Add messages
- Add internal notes
- Triage conversation
- Reply suggestion lifecycle
- Inbox list
- Email ingest

### Agent assist
- Generate suggestions
- Edit suggestion
- Approve/reject/send suggestion
- List revisions

### AI replies and summaries
- Compose AI reply
- Regenerate AI reply
- Generate conversation summary

### Intelligence
- Analyze conversation
- List conversation insights

### Suggested actions
- Generate/list suggested actions
- Accept/reject/execute actions

### Quality
- Conversation quality review
- Reply quality recording
- Reply quality analytics
- Dashboard / insights / trends

### Tickets
- List/get/update tickets
- Close/reopen
- Assign
- Auto-assign

### SLA
- Create/list SLA policies
- List violations
- Check SLA breaches

### Agents, teams, queues, routing
- CRUD agents
- CRUD teams and team members
- CRUD queues
- CRUD routing policies

### Shopify and shipping
- Connect Shopify
- Shopify OAuth install/callback
- Get order context
- Perform order actions
- Prepare Shopify support workflow
- Track shipping

### Omnichannel
- List/create channel connections
- Ingest inbound messages
- Send outbound messages
- Apply delivery events
- Provider capabilities
- Enqueue outbound messages

### Event subscriptions and workflow templates
- CRUD event subscriptions
- Seed Shopify event subscriptions
- Enable/disable subscriptions
- CRUD workflow templates
- Seed Shopify workflow templates
- Clone/publish/unpublish templates
- List workflow executions by conversation/ticket

---

## Omnichannel layer analysis

Files exist under:

```text
app/domains/customer_service/integrations/omnichannel
```

Observed providers / abstraction:

- `base.py`
- `protocol.py`
- `registry.py`
- `providers.py`
- `generic.py`
- `whatsapp.py`
- `instagram.py`
- `retry.py`
- `retry_policy.py`
- `errors.py`
- `security/signatures.py`

Core service:

```text
app/domains/customer_service/services/omnichannel.py
```

Important behavior:

- Creates/list channel connections.
- Ingests inbound provider messages into canonical customer-service conversations.
- Uses PostgreSQL advisory transaction locks for deduplication/concurrency safety around external message IDs.
- Checks external message link before creating new internal message.
- Creates customer and conversation if external thread is new.
- Links external conversation to canonical conversation.
- Links external message to canonical message.
- Publishes platform event: `customer_service.omnichannel.message.received`.
- Supports delivery event updates.
- Supports outbound provider send and outbound enqueue.

This is a strong foundation. The most important next steps later are tests and migrations for concurrency, idempotency, provider failure, and delivery status transitions.

---

## Workflow runtime platform analysis

`app/runtime` is a reusable workflow DAG runtime.

Important capabilities observed:

- DAG execution
- Node registry
- Builtin nodes
- Runtime context
- Routing edges with `when` conditions
- Join computation
- Execution policy
- Retry behavior
- Pause/resume helpers
- State snapshots
- Persistent run store abstractions
- In-memory and PostgreSQL persistence adapters
- Event sink abstraction
- Validation and diagnostics
- Human approval node
- Knowledge ingest/search nodes
- LLM generate node
- Platform job enqueue node
- Shopify nodes
- Web search / web fetch extract nodes

Important runtime modules:

- `runtime/engine/executor.py`
- `runtime/engine/execution.py`
- `runtime/engine/router.py`
- `runtime/engine/validator.py`
- `runtime/engine/state_helpers.py`
- `runtime/engine/persistence/*`
- `runtime/nodes/*`
- `runtime/waits/*`
- `runtime/control/*`

This runtime is the strategic moat of the backend. Customer-service workflows should plug into this instead of creating separate ad hoc automation systems.

---

## Workflow operational layer

### Jobs
`app/jobs` provides:

- Job repository
- Job service
- Worker
- Handler registry
- Retry/backoff
- Lease expiration
- Dead letter handling
- Replay
- Recovery
- Metrics
- Workflow job handlers

This is the right place to run durable async work such as provider sends, workflow runs, delayed jobs, and replay.

### Events
`app/platform/events` provides:

- Event publisher
- Event bus
- Event store
- Handler registry
- Event router
- Customer-service event handlers
- Workflow event handlers
- Wait-resolution handlers

This is the right place for decoupling inbound events from downstream automations.

### Waits
`app/workflow_waits` provides manual/external waits and approval/rejection endpoints. This is important for human-in-the-loop flows.

### Snapshots/timeline/diff/evaluations/quality/metrics/versions
These modules show the backend is designed for serious workflow lifecycle management:

- Version workflows before publishing.
- Snapshot workflow run state.
- Replay from snapshots.
- Compare snapshots/runs.
- View timeline.
- Run evaluations/regression checks.
- Score workflow quality and enforce deployment gates.
- Summarize metrics by workflow definition/version.

This is stronger than basic no-code workflow tooling because it already includes testing/quality/replay concepts.

---

## Agent runtime analysis

`app/agents_runtime` contains a separate agent execution layer:

- Agent runner
- Runtime context
- Event recorder and event stream
- In-memory/Postgres state stores
- Agent state machine
- Tool registry
- Tool executor
- Builtin tools
- Guardrails/approvals
- Memory store
- Planner schemas/services
- Usage budget/tracker
- Evaluation schemas/evaluator

Important builtin tools include:

- Calculator
- Echo
- Fake order lookup
- Fake refund order

This agent runtime should stay separate from the deterministic workflow runtime. Best mental model:

- **Workflow runtime** = deterministic orchestration, durable state, business process.
- **Agent runtime** = reasoning/tool-use loop, approvals, agent events, memory, usage budget.
- **Customer service domain** = product data and business rules.

Future best practice: product workflows should call agent runtime only at controlled nodes or service boundaries, not mix agent loop code directly into routers.

---

## Shopify-first product analysis

The backend already shows a Shopify-first direction:

- Shopify connection model
- Shopify order cache
- Shopify OAuth install/callback endpoints
- Shopify order lookup/actions
- Shopify order context builders
- Shopify support workflow orchestrator
- Shopify workflow catalog/templates
- Shopify workflow decisions
- Runtime Shopify nodes
- Customer-service workflow templates seeded for Shopify
- Event subscriptions seeded for Shopify

This fits the first product positioning: **AI customer service for Shopify stores**.

The product path looks like:

1. Customer message arrives from channel.
2. Ingest into canonical conversation/ticket.
3. Triage/intelligence detects intent/urgency/order references.
4. Shopify context resolver enriches with order details.
5. AI reply composer drafts a response.
6. Suggested actions/workflow decision may propose refund/reship/cancel/status update.
7. Agent approves/edits/sends.
8. Reply quality and analytics learn from human edits.
9. Workflow execution/event subscription records keep automation traceability.

This is exactly the correct journey for a paid Shopify support automation product.

---

## Important architectural boundaries to preserve

### Keep domain-owned customer service code under:

```text
app/domains/customer_service
```

Use existing folders:

- `models`
- `schemas`
- `repositories`
- `services`
- `routers`
- `integrations`
- `workflows`
- `providers`
- `inbox`
- `chat`

### Keep platform orchestration under:

```text
app/runtime
app/agents_runtime
app/jobs
app/platform/events
app/webhooks
app/workflow_* modules
app/schedules
```

### Do not create random new top-level product routers
Use domain routers and then wire through `customer_service/main.py`.

### Do not bypass services/repositories
The repo already follows a service/repository/router layering pattern. Future code should preserve it:

```text
Router -> Service -> Repository -> Model
```

Runtime/event/job integrations should usually go through services, not directly from routers.

---

## Tests and migrations readiness

The uploaded archive does not include tests or migrations. Before serious new backend development, add or upload:

1. Existing `tests/` directory.
2. Existing Alembic/migration directory.
3. Current `pyproject.toml` / `requirements.txt` / lock file if available.
4. Docker/dev environment config if not already included elsewhere.

### Test areas that should be protected first

- Customer/service CRUD flows
- Inbox/conversation/message/ticket lifecycle
- Omnichannel inbound idempotency
- Omnichannel outbound enqueue/send
- Provider signature verification
- Delivery event update behavior
- Shopify connection/order context/action flows
- Triage and conversation intelligence
- AI reply compose/regenerate
- Agent assist approval/edit/send/reject lifecycle
- Reply quality metrics and trends
- Routing policy matching
- Agent capacity selection
- SLA policy and breach detection
- Event subscriptions triggering workflows
- Workflow template clone/publish/seed
- Runtime workflow run/resume/wait/snapshot/replay
- Job retry/DLQ/replay/recovery
- Platform event publication/handler dispatch

### Migration areas to verify

- All `cs_*` tables from customer service models.
- Unique constraints for channel/external thread/message IDs.
- Enum names and values are stable.
- JSONB columns are Postgres-compatible.
- pgvector / generated tsvector columns for knowledge if used in production.
- Indexes for inbox, conversations, messages, tickets, external links, event subscriptions, routing policies.

---

## Current risks / things to verify later

1. **No tests/migrations in upload**: cannot verify pass/fail state from this archive alone.
2. **Duplicate inbox router inclusion** in `app/main.py`: may be compatibility or accidental.
3. **Large model file**: `customer_service/models/models.py` contains many domain models in one file. It works, but future scalability may benefit from model splitting while keeping imports stable.
4. **Enum migration stability**: multiple SQLAlchemy enums need migration care.
5. **Provider implementation depth**: provider abstractions exist, but real production WhatsApp/Instagram details need verification.
6. **Security for provider configs/tokens**: Shopify token field says encrypted, but encryption implementation should be verified.
7. **Agent/runtime integration boundary**: keep agent reasoning controlled and observable through workflow nodes/services.
8. **Idempotency tests are critical**: omnichannel inbound already uses advisory locks; tests must prove concurrent duplicate webhook behavior.

---

## Recommended next development sequence

### Step 1 — Add tests and migrations
Upload/add tests and migrations, then run full suite to establish baseline.

### Step 2 — Create architecture contract docs
Document boundaries:

- Platform runtime contract
- Customer-service domain contract
- Omnichannel provider contract
- Shopify support workflow contract
- Agent-assist lifecycle contract

### Step 3 — Protect omnichannel with tests
First backend hardening should focus on:

- inbound idempotency
- external conversation linking
- external message linking
- outbound enqueue/send
- delivery status update
- provider capabilities
- signature verification

### Step 4 — Protect Shopify product flow with tests
Important because first customers are Shopify stores:

- order reference extraction
- order context building
- support workflow preparation
- suggested actions
- refund/reship/cancel/status workflows

### Step 5 — Frontend alignment
When frontend is uploaded, map frontend pages/components to backend capabilities:

- Inbox center
- Conversation detail
- Ticket sidebar
- Shopify context sidebar
- AI reply composer
- Agent assist suggestion lifecycle
- Suggested actions panel
- SLA/priority/tags
- Omnichannel channel connections
- Routing policies / agents / teams / queues
- Workflow templates and event subscriptions
- Analytics / reply quality dashboard

---

## Memory-worthy project understanding

For future work, remember this architecture:

Tajeran backend is a FastAPI + SQLAlchemy platform where the first product is an AI-native Shopify-first customer-service/helpdesk domain. The backend already contains a durable workflow runtime, agent runtime, job system, platform events, waits, snapshots, timeline, diff, workflow versions, metrics, quality gates, evaluations, webhooks, schedules, and a large customer-service domain. Customer-service owns inbox, conversations, customers, tickets, SLA, tags, audit logs, macros, intelligence, suggested actions, reply quality, quality reviews, AI replies, Shopify, shipping, omnichannel, event subscriptions, routing policies, agents, teams, queues, chat, workflow templates, and workflow executions. Omnichannel already uses canonical internal conversations/messages plus external conversation/message link tables, provider registry/abstractions, and advisory-lock idempotency for inbound duplicate messages. Future development should preserve Router -> Service -> Repository -> Model layering, keep domain code under `app/domains/customer_service`, keep cross-cutting orchestration under `app/runtime`, `app/agents_runtime`, `app/jobs`, `app/platform/events`, `app/webhooks`, and `app/workflow_*`, and add tests/migrations before major changes.
