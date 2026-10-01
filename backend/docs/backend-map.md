# Backend Map — by responsibility

FastAPI app (`app/main.py`) → `app/api/router.py` mounts every router. Python files per package in brackets.

```
Request ──► api/ (HTTP)
              │
              ├─► domains/customer_service  (product: support desk)  ──┐
              ├─► workflow_operations       (versions, snapshots…)      │ call
              ├─► tcos/                     (planning "brain")          ▼
              │        └─ compiles plan ─► runtime/ (executes graph) ◄─ providers/ (Shopify, Stripe)
              └─► platform/ + tenancy/ + authentication/ (cross-cutting)
                         core/ + integrations/ + services/ + tools/ (infrastructure)
```

## 1. Entry & wiring (root of `app/`)
| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, lifespan (startup validation, checkpointer, agent runtime services), mounts `api_router` + realtime router |
| `runtime_services.py` | Builds/holds the shared runtime services (engine, registries, persistence) |
| `cognitive_runtime.py` | Builds the TCOS cognitive runtime (planner + compiler + verifier + learning) |
| `node_registration.py` | Registers workflow node types (core + product + provider) at startup |
| `identity.py` | Identity/auth policy helpers (currently modified in your branch) |

## 2. API layer — `app/api/` [39]
Thin HTTP routers only; no business logic.
- Core: `auth.py`, `contact.py`, `health.py`, `workspaces.py`, `workflows.py`, `knowledge.py`, `agents.py`, `tools.py`, `tcos.py`, `capabilities.py`, `platform.py` (jobs/schedules/webhooks/events), `workflow_operations.py`, `send_email.py`
- Product: `api/products/customer_service/` — one router per feature (inbox, conversations, customers, helpdesk, autopilot, automation, studio, workforce, analytics, channels, knowledge, learning, proactive, commercial, business_value, email_identity, intelligence) + `providers/shopify.py`

## 3. Layer A — Agentic core (the engine, product-agnostic)
### `app/runtime/` [237] — **executes** workflows
- `engine/` — DAG executor: lifecycle, join, idempotency, replay safety, completion, persistence (memory/postgres)
- `nodes/` — node types (`builtins/`: llm_generate, capability, human_approval, join_all, knowledge_search, agent_*, platform_job…), registry, executor
- `capabilities/` — capability registry, resolver, invoker (`capability.invoke`), execution policy/health/performance/outcomes, provider installation
- `objectives/` — cognition, resolution, repair, learning (objective lifecycle + policies)
- `learning/observations/` — aggregation, trends, insight candidates → approved insights
- `state/` run state/snapshot/patch · `waits/` · `control/` interrupt/resume · `resources/` · `errors/` · `utils/`

### `app/tcos/` [92] — **plans** (turns a message into a workflow)
- `planner/` — `business_ir/` (what the business wants), `planning_ir/`, `runtime/` (intent, plan candidates, evaluator, capability reasoner), `product_planning/` (registry products plug planners into), `memory/`
- `compiler/` — Planning/Business IR → Execution IR → ExecutionGraph
- `verification/` — plan verification + confidence
- `planning_repair/` · `planning_learning/` — repair failed plans, learn from outcomes
- `capabilities/` — capability catalog/scoring/advisory for the planner
- `execution/` — coordinator/adapters bridging compiled plan to runtime
- `cognitive/` — top-level cognitive runtime & objective telemetry

### `app/agents_runtime/` [26] — LLM agent loop (runner, tools, usage/budget, state machine, event stream)
### `app/workflow_operations/` [40] — lifecycle ops around workflows: versions, deployments, snapshots/replay, diff, timeline, waits, metrics, evaluations/regression, quality
### `app/services/`, `app/tools/` — knowledge ingest/chunk/embed/retrieve/rerank, workflow_runner, email_service; MCP client, tool helpers (cache, ratelimit, http)

## 4. Layer B — Product: `app/domains/customer_service/` [293]
| Folder | Responsibility |
|---|---|
| `models/` [16] | SQLAlchemy tables (conversations, omnichannel, routing, outcomes, quality, commercial…) |
| `schemas/` [55] | Pydantic request/response models |
| `repositories/` [30] | DB access |
| `services/` [79] | Business logic: inbox, assignment/routing (`routing_engine/`), SLA, AI replies, autopilot, agent assist, analytics, billing, macros, customer 360, quality/reply-quality, knowledge, shopify_* services |
| `services/workforce/` | agents, teams, queues, capacity, availability, time off |
| `services/support/` | Customer-support planning on top of TCOS: objective, planning, resolution, repair, outcome, learning, commerce context |
| `inbox/` · `chat/` | Message threading & inbox service; chat |
| `integrations/omnichannel/` | WhatsApp, Instagram, generic channel adapters, retry, security |
| `integrations/shopify/` | OAuth, client, webhooks, lifecycle (Shopify install side) |
| `providers/` | commerce / shipping provider abstractions |
| `workflows/` | message classifier, reply-suggestion workflow, trigger handlers, runtime bridge |
| `runtime/nodes/` | product-specific workflow nodes (customer_chat, order_ref, outcome recording…) |
| `jobs/` `events/` `realtime/` `security/rbac.py` | job handlers, event handlers, websocket events, role permissions |

## 5. Layer C — Providers: `app/providers/` [7]
- `shopify/runtime/` — Shopify capability nodes + registration
- `stripe/webhooks.py` — Stripe webhook handling

## 6. Platform (cross-cutting)
| Package | Responsibility |
|---|---|
| `tenancy/` | Workspaces/accounts, membership, tenant context, usage, working calendar, deletion |
| `authentication/` | Users, sessions, login/signup service |
| `platform/jobs/` | Durable job queue: worker, lease, retry, dead-letter, replay, recovery |
| `platform/schedules/` | Cron-like scheduler |
| `platform/events/` | Event bus/store/registry; handlers that resume workflows/waits |
| `platform/webhooks/` | Inbound webhook ingestion + provider registry |
| `platform/realtime/` | WebSocket hub, presence, publisher |
| `platform/composition.py` | Assembles platform services |

## 7. Infrastructure — `app/core/`, `app/integrations/`, `app/models/`
- `core/` — config, environment, startup validation, Redis, RabbitMQ, DB session, CORS, observability, http_safety (SSRF), `security/` (crypto, secrets), `providers/llm/` (OpenAI/LangChain clients, factory, resilience), token budget, checkpointer
- `integrations/` — outbound gateway with circuit breaker, policy, metrics
- `models/` — shared base models/schemas

## 8. Outside `app/`
`migrations/` (Alembic) · `tests/` (mirrors the packages above) · `scripts/` (job_worker.py, migration check, backups, healthcheck) · `infra/` (Dockerfile, compose dev/prod, searxng) · `docs/` (architecture 01–11, runtime, planning_system, capability map)

## Dependency rule
`api → domains/providers → tcos → runtime → platform/tenancy/core`. Lower layers must not import upward.
Known violations (see CLAUDE.md): `domains/customer_service/services` importing `app.runtime.*`, product files importing `app.tcos.*` to register planners, `providers/shopify/runtime` importing `app.runtime`.
