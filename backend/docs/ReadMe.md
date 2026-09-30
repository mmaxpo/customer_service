## Tajeran agents can connect to any MCP-compatible tool.
### This looks big.
## But it’s what lets you scale to $100M SaaS.
### That is positioning power.

### 📌 7) Your Current Level

- Right now, honestly:

- You’re operating at:

- Senior Platform Engineer + AI Infra Founder level

- Most startups buy this.
You built it.

### Phase 2 – Platformization
- 1.	Agent Template Registry
- 2.	Workflow Builder UI
- 3.	Tool Registry
- 4.	Multi-agent orchestration
- 5.	Billing layer
- 6.	Tenant separation
- 7.	Usage tracking
- 8.	Deployment automation
- 9. Create first Shopify-focused support agent
- 10. Design agent template architecture
- 11. Design monetization strategy

### The workflow base you need (covers most real work) 

A) Trigger (start)
	•	OnMessage (chat input)
	•	later: OnTicketCreated, OnOrderUpdated, OnWebhook, Cron

B) Context / Memory
	•	SetVars (write variables)
	•	GetVars (read variables)
	•	later: session memory, thread memory, “case memory”

C) Knowledge / Retrieval
	•	KBSearch (your hybrid_search tool)
	•	later: multi-query retrieval, page/tree retrieval, rerank toggles

D) Model
	•	LLM (prompt + model settings)
	•	Classifier (LLM that outputs a label, used for routing)

E) Tools / Actions
	•	ToolCall (call a tool by name with args mapping)
	•	later: Shopify actions, email send, ticket update, refund create

F) Routing / Control flow
	•	Router (branch by label/condition)
	•	IfElse (simple boolean expression)
	•	later: loops, retries, fallbacks, parallel, timeouts

G) Human-in-the-loop
	•	AskHuman (pause + wait for input)
	•	later: approvals, escalations, agent handoff

H) Output
	•	Respond (final message)
	•	later: multi-channel output (email/chat)

That’s enough to ship “template workflows” fast.

### This is the foundation of:

- “Zapier + LangGraph + MCP for AI Agents”
- Which is exactly what Tajeran is becoming.

## Build Plan (phased, minimal → powerful)

Phase 0 — Lock the foundation you already have
	•	DAG workflow saved as JSON {nodes, edges}
	•	Node execution engine (sequential) already works

Phase 1 — State contract + node I/O (your “LangGraph-like” core)
	•	Single shared RunState
	•	Every node: (state, nodeConfig) -> { patch, outputs }
	•	Runtime merges patches, writes outputs to state.last.byNode[nodeId]

Phase 2 — Control nodes (the real unlock)
	•	Router node (rule router first, LLM router later)
	•	Join node (wait-for-all / aggregator)
	•	Foreach node (static fan-out)
	•	Human approval node (interrupt/resume)

Phase 3 — Parallel execution + reliability
	•	Topological execution + concurrency limits
	•	Retries/timeouts per node
	•	Streaming logs per node
	•	Persist run state + resumability

Phase 4 — Dynamic fan-out patterns (orchestrator-worker)
	•	foreach + “spawn workers” node (dynamic items)
	•	Join + Synthesizer node

┌─────────────────────────────┐
│   Workflow JSON Spec (v1)   │  ← Save/Load/Templates
└─────────────▲───────────────┘
              │
┌─────────────┴───────────────┐
│     Node Catalog (v1)       │  ← Agent/Tool/Router defs
└─────────────▲───────────────┘
              │
┌─────────────┴───────────────┐
│    Runtime Executor Core    │  ← DAG engine
└─────────────────────────────┘


### 🧠 Layer 1 — Runtime Engine (Core Brain)

“How workflows actually run”

This is your most valuable IP.

If this is solid → you win.

### 1️⃣ RunState (Shared Memory)

Purpose

One object that lives during execution.

Every node reads/writes here.

Must Contain
RunState = {
  input: any,
  vars: {},          // user variables
  memory: {},        // agent memory
  results: {},       // node outputs
  meta: {},          // tracing/debug
  errors: {},
  status: "running|paused|done|failed"
}
Rules

✅ Raw data only
✅ No formatted prompts
✅ Serializable
✅ Persistable (DB/Redis later)

Why:

→ enables resume, replay, debugging
2️⃣ Node I/O Contract

Every node must follow:
execute(state, config) → {
   statePatch,
   output,
   route?
}

Rules:

✅ Stateless nodes
✅ No global mutation
✅ Deterministic

Why:

→ nodes become portable plugins

3️⃣ DAG Executor

Purpose

Walk graph + schedule nodes.

Responsibilities
	•	Topological order
	•	Track dependencies
	•	Parallel scheduling
	•	Retry handling
	•	Timeouts
	•	Error bubbling

Internal Data

NodeStatus = {
  pending | running | done | failed | skipped
}

Core Loop
while nodes remain:
  find runnable nodes
  execute
  merge state
  update status

4️⃣ Router + Conditions

Explicit Routing (Your Choice ✅)

Edges have rules:
{
  "source": "router1",
  "target": "billing_node",
  "condition": "route == 'billing'"
}

Runtime Logic

Why this matters:Your System
 Visual
Clear
Deterministic
5️⃣ Join / Parallel Control

Problem

Multiple branches → need merge.

Join Node
{
  "type": "join",
  "mode": "all" | "any"
}
Engine Behavior

Wait until:
	•	ALL parents done → continue
	•	ANY parent done → continue


### Implementation Sequence (the “do this first” checklist)
	1.	Add validator skeleton + wire it into executor (even if validator only checks node ids first)
	2.	Expand validator until it covers all planned rules
	3.	Add diagnostics module + wire it into deadlock return
	4.	Add/adjust skip event logic (only if needed)
	5.	Write pytest suite

## 📦 Layer 2 — Node Catalog (Capabilities Layer)
“What can workflows do?”

This is your product layer.

⸻

1️⃣ Node Definition Schema

Every node registered as:
NodeType = {
  type: "agent.langgraph",
  configSchema: {},
  inputSchema: {},
  outputSchema: {},
  executor: fn
}

Why:

→ Validation
→ UI auto-forms
→ Marketplace later

⸻

2️⃣ Node Categories

Core Set (v1)

Category
Purpose
Trigger
Entry
Agent
Reasoning
Tool
Action
Router
Decision
Join
Sync
Transform
Data
Human
Approval
Output
Send

3️⃣ Tool vs MCP

Native Tools

Fast, internal

MCP Tools

External ecosystem

Runtime treats both same:
call(tool.execute)

Why:

→ Vendor neutral

⸻

4️⃣ Human-in-the-Loop Node

Special node:

return {
  status: "paused",
  interrupt: {...}
}

Runtime:

→ Save state
→ Wait
→ Resume

This is enterprise gold.

⸻

5️⃣ Subgraphs (Later)

Nodes that run mini-workflows.

node: subgraph(order_fulfillment)
Future scaling.

⸻

## 📄 Layer 3 — Workflow JSON Spec (Storage Layer)

“How workflows are stored and shared”

This is UI/backend contract.

⸻

1️⃣ Core Structure
{
  "version": "1.0",
  "nodes": [],
  "edges": [],
  "stateSchema": {},
  "metadata": {}
}
2️⃣ Node Format
{
  "id": "n1",
  "type": "agent.langgraph",
  "config": {...},
  "ui": {...}
}
UI info separated.

⸻

3️⃣ Edge Format

{
  "source": "n1",
  "target": "n2",
  "condition": "route=='billing'"
}

4️⃣ Validation Layer

Before run:
validate(workflow.json)

Check:
	•	cycles
	•	missing nodes
	•	broken edges
	•	schema mismatch

Prevents runtime crashes.

⸻

5️⃣ Versioning

Later:
🏁 Final Summary

Build Order

✅ Layer 1 first (engine)
✅ Layer 2 second (nodes)
✅ Layer 3 last (JSON)
MVP Goal
Trigger
 → Router
 → KB
 → Agent
 → Response


Next Step Options (pick order I’d do)
	1.	Standardize error format across runtime (so API always returns the same meta shape for error, invalid_workflow, deadlock, etc.)
	2.	Add graph-level invariants (exactly one trigger? at least one response? optional strictness)
	3.	Add parallel execution (your join/all design is now ready for it)
	4.	Add execution tracing IDs (per-run run_id, per-node span_id) for observability

---
### ✅ Test 1 — Linear (Trigger → kb.search → response)
```json
{
  "workflow": {
    "nodes": [
      { "id": "t1", "data": { "nodeType": "trigger.message", "input": "refund policy" } },
      { "id": "s1", "data": { "nodeType": "kb.search", "top_k": 3 } },
      { "id": "r1", "data": { "nodeType": "response" } }
    ],
    "edges": [
      { "id": "e1", "source": "t1", "target": "s1" },
      { "id": "e2", "source": "s1", "target": "r1" }
    ]
  },
  "message": ""
}
```
### ✅ Test 2 — Conditional routing (Trigger → router.rules → A|B → response)
```json
{
  "workflow": {
    "nodes": [
      { "id": "t2", "data": { "nodeType": "trigger.message", "input": "billing: I was charged twice" } },
      {
        "id": "rt",
        "data": {
          "nodeType": "router.rules",
          "default_route": "default",
          "rules": [
            { "when": "vars.input == 'billing: I was charged twice'", "route": "billing" }
          ]
        }
      },
      { "id": "A", "data": { "nodeType": "set.variable", "key": "path", "value": "A: billing path ran" } },
      { "id": "B", "data": { "nodeType": "set.variable", "key": "path", "value": "B: refund path ran" } },
      { "id": "r2", "data": { "nodeType": "response" } }
    ],
    "edges": [
      { "id": "e1", "source": "t2", "target": "rt" },

      { "id": "e2", "source": "rt", "target": "A", "condition": "billing" },
      { "id": "e3", "source": "rt", "target": "B", "condition": "refund" },

      { "id": "e4", "source": "A", "target": "r2" },
      { "id": "e5", "source": "B", "target": "r2" }
    ]
  },
  "message": ""
}
```
### ✅ Test 3 — Join (Trigger → task1 + task2 → join.all → response)
```json
{
  "workflow": {
    "nodes": [
      { "id": "t3", "data": { "nodeType": "trigger.message", "input": "start" } },

      { "id": "task1", "data": { "nodeType": "set.variable", "key": "o1", "value": "out1" } },
      { "id": "task2", "data": { "nodeType": "set.variable", "key": "o2", "value": "out2" } },

      { "id": "j1", "data": { "nodeType": "join.all", "mode": "concat_text", "separator": " | " } },
      { "id": "r3", "data": { "nodeType": "response" } }
    ],
    "edges": [
      { "id": "e1", "source": "t3", "target": "task1" },
      { "id": "e2", "source": "t3", "target": "task2" },

      { "id": "e3", "source": "task1", "target": "j1" },
      { "id": "e4", "source": "task2", "target": "j1" },

      { "id": "e5", "source": "j1", "target": "r3" }
    ]
  },
  "message": ""
}
```


⬜ Runs inbox endpoint (list paused/done)
⬜ Ownership checks (security)
⬜ Run state endpoint (optional but very helpful)
⬜ Tests for the new endpoints


Suggested order (fastest with best payoff)
	1.	Edge when contract (safe structured conditions)
	2.	router.rules node
	3.	join node semantics
	4.	subworkflow.call node (composition = huge leverage)
	5.	ReactFlow MVP UI
	6.	Add real parallel scheduler
	7.	Add spawn.workers (child runs) for orchestrator-worker


Now: your plan (finish “Part 6 → 8” = real parallel)

You’re right to finish parallelism before templates/UI.

What “real parallel” means in your engine

Right now, your DAG executor does:
	•	compute runnable nodes
	•	runs only ready[0]
So it’s “DAG-aware” but single-worker sequential.

We want:
	•	run all runnable nodes concurrently (up to a limit)
	•	keep determinism + safe state merges
	•	keep events/persistence consistent
	•	keep router/join semantics correct
	•	keep loop semantics correct

⸻

✅ Plan: Step 6–8 (Parallel execution + safe merge + deterministic events)

Step 6 — Parallel scheduler (same process)

Add to execute_workflow_dag():

New options
	•	max_concurrency: int = 8 (or from ctx.config)
	•	ready_batch_size optional

Core change
	•	instead of executing nid = ready[0]
	•	execute a batch: batch = ready[:max_concurrency]
	•	run them using asyncio.gather(...)

But we must handle state writes safely.

So: each node runs against a snapshot and returns a patch/result, then we merge patches in a deterministic order.

⸻

Step 7 — Safe merge strategy (deterministic)

We define:
	•	pre_state = copy.deepcopy(state) (or shallow copy OK if you treat state as immutable during node runs)
	•	run nodes concurrently, each returns:
	•	node_result with patch, output, meta, route, status, etc.
	•	merge in deterministic order:
	•	sort by node_id (or by topo order if you store it)
	•	apply _merge_patch sequentially

Rule
	•	vars: last-writer-wins by merge order
	•	last: last merged patch wins (deterministic)
	•	results[node_id]: always safe (unique key)
	•	meta.node_meta_by_id[node_id]: safe (unique key)

This works for 95% of your workflows.

(If later you want conflict detection: add meta["conflicts"].)

⸻

Step 8 — Correctness for router/join/loop under parallel

We need 3 special rules:

(A) Routers
A router node produces a route that gates edges.
If router and its downstream are in same “ready” set — that downstream should NOT run until router finished and gating evaluated.

Your current is_runnable() requires parents finished, so downstream won’t be ready until router finished. ✅ So parallel is safe.

(B) Join
Join should run only when all parents finished.
Also safe.

But: we must compute join inputs from parents after the batch finishes and state.results updated. We already do join injection right before running join. Safe.

(C) Control loop
Loop relies on rewinding finished sets.
In parallel mode, just ensure:
	•	control.loop is executed alone in its batch or applied after batch merge.
Simplest clean approach:
	•	if a batch contains "control.loop", run it as a single-node batch (no concurrency in that tick).

That keeps behavior simple and prevents weird multi-reset races.

⸻

Phase 1
--------
- SLA 
- Assignment
  * audit logs
  * analytics
  * workload reports
  * AI learning
- Tags
-  Internal notes
-  Macros
-  Auto-triage

Customer service capability:
70–80%

Phase 2
--------
Suggested actions
AI quality review
Conversation intelligence
Workflow marketplace

AI capability:
70–85%

Phase 3
--------
Shopify
Gmail
Stripe
Shipping APIs
Knowledge

Real-world usefulness:
90%+

Phase 4
--------
React frontend
Template marketplace
Multi-agent automation

## Phase A — finish runtime core
✓ snapshots
✓ replay
✓ timeline
✓ human approval
✓ waits
✓ state diff engine
✓ execution comparison
✓ visual debugger
- Because after this your runtime becomes:
Workflow
    ↓
Pause
    ↓
Resume
    ↓
Replay
    ↓
Debug
    ↓
Compare

### Phase B — customer service
-Inbox
Tickets
SLA
Shopify integration
Analytics
Knowledge
AI suggestions
Workflow templates
Omnichannel

## Phase C — moon phase
- Evaluation engine
Regression detector
Workflow scoring
Self-improving workflows
- because then you will have:
- real customer workflows
real failures
real approvals
real ticket history
real analytics

## The long-term target becomes:
Customer runs workflow
        ↓
Snapshots collected
        ↓
Replay failures
        ↓
Compare runs
        ↓
Evaluate quality
        ↓
Detect regressions
        ↓
Score workflow
        ↓
Generate improvements
        ↓
Human approves
        ↓
New workflow version



To finish an MVP product: about 7 major steps.

1. Finish routing automation
    Policy-based auto-route from omnichannel inbound is now started. Next: policy priority, fallback policy, escalation policy.
2. Agent/team management
    Agents, teams, skills, availability, max workload.
3. Production inbox UI contract
    Better inbox queue: sorted by SLA risk, priority, channel, assignment, unread.
4. Shopify support workflows
    Order lookup, refund/cancel/change address, damaged item, shipping status.
5. Knowledge + AI reply loop
    KB-grounded suggested replies, approve/edit/send, quality tracking.
6. Workflow template marketplace foundation
    Save, version, deploy, run, measure templates.
7. Production hardening
    permissions, rate limits, webhook security, observability, billing, onboarding.


Tajeran Customer Service Platform Roadmap

Current Foundation (Completed)

Workflow Runtime

* Workflow execution engine
* Durable run state
* Pause / Resume
* Human approval waits
* Time waits
* Event waits
* Workflow snapshots
* Workflow replay
* State restoration
* Timeline debugger foundation
* State diff engine
* Workflow scheduling
* Workflow concurrency protection
* Workflow versioning
* Workflow deployments
* Workflow evaluations
* Workflow regression foundations

Agent Runtime

* Custom agent runtime
* Tool execution loop
* Approval handling
* Event store integration
* State store integration
* Budget tracking
* Usage tracking
* Streaming support

Customer Service Foundation

* Customers
* Conversations
* Messages
* Tickets
* Inbox
* Tags
* Notes
* Macros
* Assignment tracking
* SLA tracking
* Audit trail
* Agent assist foundation

Omnichannel Foundation

* Channel connections
* Omnichannel inbound
* Omnichannel outbound
* Delivery tracking
* External message mapping
* External conversation mapping
* Event publishing

Workflow Automation Foundation

* Workflow templates
* Workflow template cloning
* Workflow template versioning
* Workflow template deployment
* Workflow template lifecycle
* Event subscriptions
* Subscription enable / disable
* Subscription validation
* Workflow execution tracking
* Workflow execution history

Platform Infrastructure

* Jobs
* Retries
* Dead letter queue
* Event bus
* Event handlers
* Webhooks
* Scheduling
* Metrics foundation

Test Coverage

* 278+ passing tests
* Workflow execution tests
* Subscription tests
* Template lifecycle tests
* Execution tracking tests
* Idempotency tests
* Concurrency tests
* Ownership/security tests
* Pagination tests
* Fan-out tests

--------------
Phase 1 — Shopify Support Automation (Highest Priority)

Goal:

First paying Shopify customers.

Shopify Integration

Merchant Connection

* Shopify OAuth
* Store installation
* Store synchronization
* Token management

Order Lookup

* Get order by email
* Get order by order number
* Get order by customer
* Order timeline
* Fulfillment state

Shipping Lookup

* Tracking number lookup
* Shipment status lookup
* Carrier information
* Delivery status

Refund Workflow

* Refund eligibility check
* Refund calculation
* Refund approval flow
* Refund execution
* Refund audit trail

Cancel Workflow

* Cancellation eligibility
* Approval flow
* Cancellation execution
* Audit trail

Address Change Workflow

* Address validation
* Fulfillment check
* Address update
* Audit trail

Damaged Item Workflow

* Evidence collection
* Replacement flow
* Refund flow
* Escalation flow

⸻

Phase 2 — Knowledge + AI Reply System

Goal:

AI support assistant that agents actually use.

Knowledge Base

Knowledge Management

* KB ingestion
* KB search
* Hybrid retrieval
* Reranking

AI Reply Suggestions

Reply Generation

* KB grounded replies
* Order context injection
* Customer context injection
* Ticket context injection

Agent Review

* Approve
* Edit
* Reject

Quality Tracking

* Acceptance rate
* Edit rate
* Rejection rate
* Resolution rate

Future Learning Loop

* Track accepted replies
* Track edited replies
* Track rejected replies
* Workflow improvement signals

⸻

Phase 3 — Routing & Automation Engine

Goal:

Automatically place work in the correct queue.

Routing Policies

Policy Rules

* Priority routing
* VIP routing
* Intent routing
* Channel routing
* Order-value routing

Skills Routing

Skills

* Billing
* Refunds
* Shipping
* Technical
* Escalations

Assignment

* Best-fit routing
* Team routing
* Agent routing

Escalations

Escalation Rules

* Urgent ticket
* VIP customer
* SLA breach
* High-value order

Fallback Routing

* General queue
* Unassigned queue
* Escalation queue

⸻

Phase 4 — Production Inbox

Goal:

Single screen support operation.

Inbox Queue

Sorting

* SLA risk
* Priority
* Assignment
* Channel
* Newest activity

Agent View

Customer Context

* Customer profile
* Order history
* Conversation history

Ticket Context

* Ticket status
* Priority
* SLA status

Workflow Context

* Running workflows
* Pending approvals
* Workflow execution history

Suggested Actions

* Suggested replies
* Suggested workflows
* Suggested macros

⸻

Phase 5 — Agent & Team Management

Goal:

Manage support teams.

Agents

Agent Profile

* Name
* Email
* Status
* Skills

Capacity

* Current workload
* Maximum workload
* Queue visibility

Teams

Team Management

* Teams
* Skills
* Ownership
* Routing targets

⸻

Phase 6 — Production Hardening

Goal:

Ready for real merchants.

Security

Authentication

* Permissions
* Roles
* Access control

Webhook Security

* Shopify signature validation
* Replay protection
* Secret rotation

Reliability

Protection

* Rate limiting
* Idempotency
* Retry protection

Observability

* Logs
* Metrics
* Traces
* Alerts

Workflow Monitoring

* Failures
* Dead letters
* Queue depth
* Execution metrics

Billing Foundation

Usage Tracking

* Workflow runs
* AI usage
* Message volume
* Seats

⸻

Phase 7 — Workflow Marketplace

Goal:

Scale beyond customer service.

Template Marketplace

Template Catalog

* Browse templates
* Install templates
* Clone templates

Versioning

* Draft
* Published
* Archived

Metrics

* Runs
* Success rate
* Usage

Distribution

* Internal templates
* Public templates
* Partner templates

⸻

Future Expansion

After Customer Service succeeds:

Additional Products

* Sales Automation
* Marketing Automation
* HR Automation
* Operations Automation
* Internal AI Agents
* Enterprise Agent Orchestration
-------
Pending for Phase 3

1. Team Ownership / Security Tests
User A creates team
User B cannot:
  - view it
  - update it
  - delete it
  - add/remove members

2. Duplicate Membership Test
Add same agent twice
↓
should not create duplicate membership

3. Agent Availability + Workload Routing
available agents only
active agents only
skip unavailable agents
skip over-capacity agents

4. Skills-Based Assignment
refund ticket → refund-skilled agent
shipping ticket → shipping-skilled agent
damaged item → escalation/returns-skilled agent
5. Team-Based Routing Policy Integration
routing policy targets team_id
event/message comes in
system assigns to best agent in that team
6. Queue Workload Visibility
team queue
assigned count
open ticket count
urgent count
SLA risk count
available agents
7. Agent Capacity
max_workload
current_workload
can_accept_ticket

Recommended Build Order
1. Security tests for teams
2. Duplicate membership test
3. Agent workload/capacity service
4. Best-agent selection service
5. Team routing integration
6. Team queue workload endpoint


-------Frontend---------

1. Inbox UI
    /app/inbox with conversation list + selected conversation + ticket sidebar.
2. Conversation detail + AI reply
    Inside Inbox page first, not separate route yet.
3. Ticket sidebar
    Customer, Shopify order, SLA, tags, assigned agent.
4. Agents / Teams / Routing UI
    Add /app/agents or /app/routing.
5. Workflow templates + Shopify automation page
    Improve /app/workflows, and make template cards open /app/workflows/builder?template=refund.
6. Knowledge UI polish
    You already have /app/knowledge.
7. Analytics + Runs UI
    You already have /runs; later move/duplicate into /app/runs.

Main decision: do not start with dashboard. Dashboard should summarize real product pages. Start with Inbox, because that is the product center.
Next implementation should be:
src/lib/api/customer-service.ts
src/app/api/customer-service/inbox/route.ts
src/app/api/customer-service/conversations/[conversationId]/route.ts
src/app/api/customer-service/conversations/[conversationId]/messages/route.ts
src/app/api/customer-service/conversations/[conversationId]/ai-replies/regenerate/route.ts
src/app/(app)/app/inbox/page.tsx
src/features/customer-service/inbox/components/*

---------------

Phase 1: Inbox manual reply to chat
- Admin sees website chat in Inbox
- Admin sends reply
- Reply writes to conversation + chat session
- Widget receives it by polling

Phase 2: Chatbot workflow settings
- Choose workflow for chatbot
- Enable/disable auto-answer
- Confidence threshold
- Human handoff toggle

Phase 3: AI answer workflow
- trigger.message
- kb.search
- llm.generate
- reply.customer_chat

Phase 4: Shopify workflow
- extract order number
- shopify.get_order
- llm.generate
- reply.customer_chat

Phase 5: Production widget
- CORS hardening
- rate limiting
- visitor identity
- typing state
- unread count
- branding
- Shopify install injection

----------------------------
--------------------------
Phase 1 — Customer Service Hardening (Must Complete)

1. Canonical Intent System

Problem:

Multiple intent names exist:

* refund_request
* cancellation
* cancellation_request
* tracking_request
* shipping_delay
* damaged_item

Actions:

* Create CustomerIntent enum
* Migrate Conversation Intelligence
* Migrate Suggested Actions
* Migrate AI Reply Composer
* Migrate Shopify Support Orchestrator
* Migrate Triage
* Migrate Workflow Classifier

Goal:

Single source of truth for customer intents.

⸻

2. Conversation Timeline API

Create:

GET /customer-service/conversations/{conversation_id}/timeline

Timeline should merge:

* Customer messages
* Agent messages
* Internal notes
* Tag events
* Assignment events
* SLA events
* Suggested actions
* AI reply generation
* Workflow executions
* Shopify actions
* Audit events

Goal:

Single chronological activity feed.

Required by Inbox UI.

⸻

3. Customer 360 Service

Create service returning:

* Customer
* Conversations
* Tickets
* Orders
* Tags
* SLA state
* Timeline summary

Goal:

Power right sidebar in Inbox.

⸻

4. Omnichannel Identity Resolution

Support:

* Email identity
* Phone identity
* Shopify customer identity
* Website chat identity
* Instagram identity
* WhatsApp identity

Goal:

Merge customer activity into one profile.

⸻

5. Customer Merge Capability

Ability to merge:

Customer A → Customer B

Migrates:

* Conversations
* Tickets
* Tags
* Orders
* External links

Goal:

Real support-team operational requirement.

⸻

Phase 2 — Workflow & Automation Hardening

6. Workflow Trigger Idempotency

Validate:

* Same event 10x
* Same webhook 10x
* Same inbound message 10x

Result:

Single workflow execution.

⸻

7. Workflow Execution Timeline Events

Every workflow execution should emit:

* Started
* Paused
* Resumed
* Completed
* Failed

Visible in conversation timeline.

⸻

8. SLA Automation

Support:

* First response breach
* Resolution breach
* Escalation workflow
* Manager notification

Goal:

Production SLA management.

⸻

Phase 3 — Shopify Support Hardening

9. Dangerous Action Protection

Protect:

* Refund twice
* Cancel twice
* Duplicate return creation

Goal:

Prevent costly mistakes.

⸻

10. Shopify Order Context Service

Single service returns:

* Order
* Fulfillment
* Tracking
* Refunds
* Risk indicators

Goal:

Inbox loads all order context from one endpoint.

⸻

Phase 4 — Inbox Production Readiness

11. Conversation Read Models

Optimized queries for:

* Inbox list
* Conversation detail
* Timeline
* Customer 360

Goal:

Avoid N+1 query growth.

⸻

12. Conversation Search

Search:

* Customer name
* Email
* Order number
* Message content
* Ticket number

Goal:

Support-team usability.

⸻

13. Saved Views

Support:

* Open
* Waiting Customer
* Waiting Agent
* High Priority
* SLA At Risk

Goal:

Operational support workflows.

⸻

Phase 5 — Testing Expansion

Timeline Tests

Validate:

* Event ordering
* Event visibility
* Event filtering

⸻

Omnichannel Identity Tests

Validate:

* Same customer across channels

⸻

Customer Merge Tests

Validate:

* Data migration integrity

⸻

SLA Automation Tests

Validate:

* Escalation triggers

⸻

Workflow Idempotency Tests

Validate:

* Duplicate events produce one execution

⸻

Shopify Safety Tests

Validate:

* Duplicate refund protection
* Duplicate cancellation protection

⸻

Performance Tests

Validate:

* 5,000+ message conversations
* Large inboxes
* Timeline scalability


----------------------------------------
- Tier 4 — Observability / Diagnostics
- workflow/node latency
- provider latency/failure metadata
- run failure diagnostics
- timeline/debug trace completeness
- per-tenant usage/cost visibility

- Tier 5 — Customer Service Production Completeness
- macros safety
- internal notes permissions
- ticket status transition guards
- assignment/routing audit consistency
- agent availability/workload correctness
- SLA pause/business-hours later

- Tier 6 — Knowledge / AI Answer Safety
- source-grounded answers
- no-answer fallback
- stale knowledge detection
- confidence thresholds
- hallucination guard tests
- tenant isolation for knowledge search

- Tier 7 — Workflow Builder Product Hardening
- invalid graph validation
- cycle/branch/join edge cases
- node config schema validation
- publish/versioning/rollback
- workflow template safety
- frontend-builder compatibility contracts

- Tier 8 — Runtime Platform Hardening
- job queue crash recovery
- stuck run detection
- tenant rate limits
- retries/dead-letter observability
- long-running run cleanup
- replay/debug UX data completeness

- Tier 9 — Security / Multi-tenant Production
- strict user_id isolation
- webhook signature verification
- provider secret encryption
- admin/dev endpoint guards
- audit log completeness
- permission/RBAC tests

- Tier 10 — Scale / Performance
- DB indexes
- pagination everywhere
- N+1 query checks
- large inbox performance
- concurrent webhook load
- queue throughput tests



Main things still missing:

1. Security blocker: Shopify token says TODO encryption. Must fix before production.
2. Scale blocker: Inbox/list endpoints can load too much data.
3. Workflow safety blocker: Customer-service workflow templates should validate graph before create/update/publish/subscription.
4. SLA business logic gap: You have SLA, but no clear business-hours/calendar SLA.
5. RBAC gap: Tenant isolation exists, but role permissions are not mature.
6. Observability gap: Runtime has events/snapshots, but customer-service action latency/metrics should be more standard.

pytest tests/customer_service -q

-------------------------
Realtime Architecture Plan

Goal

Tajeran needs a shared realtime backend foundation so product features do not depend on manual refresh or frontend polling.

The Inbox should update instantly when:

* a customer sends a message
* an AI reply is created
* a workflow starts, succeeds, fails, or pauses
* human approval is required
* SLA changes
* Shopify actions finish
* new support events arrive from channels

This should be built as a reusable backend service, not only as an Inbox-specific feature.

⸻

1. Target Structure

app/
  realtime/
    __init__.py
    schemas.py
    hub.py
    publisher.py
    router.py
    auth.py
    codec.py
  domains/
    customer_service/
      realtime/
        __init__.py
        events.py
        publisher.py
  platform/
    events/
      ... existing durable/internal event system ...
frontend/
  src/
    lib/
      realtime/
        client.ts
        events.ts
    features/
      customer-service/
        inbox/
          hooks/
            useInboxRealtimeStream.ts

⸻

2. Backend Realtime Layer

app/realtime/schemas.py

Defines the common event contract.

Every realtime event should have:

{
    "id": "uuid",
    "type": "customer_service.message.created",
    "scope": "customer_service",
    "user_id": "uuid",
    "entity_type": "conversation",
    "entity_id": "uuid",
    "payload": {},
    "created_at": "iso_datetime"
}

The frontend should never guess what happened. It should receive a clear event type from the backend.

⸻

app/realtime/hub.py

Responsible for live connected clients.

V1 can be in-memory:

user_id -> active SSE connections

Responsibilities:

* register client connection
* unregister disconnected client
* publish event to connected user
* filter events by user
* optionally filter by scope

V1 is enough for local/dev/single-instance.

Later production version should use Redis Pub/Sub so multiple API workers can broadcast to the same user.

⸻

app/realtime/publisher.py

Single backend API for publishing realtime events.

Example:

await realtime_publisher.publish(
    user_id=user_id,
    type="customer_service.message.created",
    scope="customer_service",
    entity_type="conversation",
    entity_id=conversation_id,
    payload={
        "conversation_id": str(conversation_id),
        "message_id": str(message_id),
        "sender_type": "customer",
        "preview": "Where is my order #1005?",
    },
)

Any domain can use this without knowing about SSE internals.

⸻

app/realtime/router.py

Expose authenticated SSE endpoint:

GET /realtime/stream

Optional query params:

/realtime/stream?scope=customer_service

The response should be:

Content-Type: text/event-stream

SSE events should look like:

event: customer_service.message.created
data: {"id":"...","type":"customer_service.message.created",...}

Also send heartbeat events every 20–30 seconds to keep the connection alive.

⸻

3. Customer Service Realtime Events

Create:

app/domains/customer_service/realtime/events.py
app/domains/customer_service/realtime/publisher.py

Customer-service should publish these events:

customer_service.conversation.created
customer_service.message.created
customer_service.ai_reply.created
customer_service.workflow.started
customer_service.workflow.succeeded
customer_service.workflow.failed
customer_service.workflow.paused
customer_service.approval.required
customer_service.sla.updated
customer_service.shopify_action.completed

⸻

4. Where Backend Should Publish Events

Customer sends chat widget message

In CustomerChatService.add_inbox_customer_message_for_chat_session:

publish customer_service.message.created

Payload:

{
  "conversation_id": "...",
  "message_id": "...",
  "sender_type": "customer",
  "preview": "Where is my order #1005?"
}

⸻

AI replies to chat widget

In CustomerChatService.add_inbox_ai_message_for_chat_session:

publish customer_service.ai_reply.created

⸻

Agent replies from Inbox

In Inbox reply service:

publish customer_service.message.created

Payload should include:

{
  "sender_type": "agent"
}

⸻

Workflow job changes

When workflow.run job succeeds, fails, dead-letters, or pauses:

publish customer_service.workflow.succeeded
publish customer_service.workflow.failed
publish customer_service.workflow.paused
publish customer_service.approval.required

⸻

Suggested action execution

When suggested action creates workflow execution:

publish customer_service.workflow.started

When it completes:

publish customer_service.shopify_action.completed

⸻

5. Frontend Structure

src/lib/realtime/client.ts

Shared SSE client.

Responsibilities:

* open EventSource("/api/realtime/stream?scope=customer_service")
* reconnect automatically
* parse event data
* dispatch typed events
* close connection on unmount

⸻

Next.js API Proxy

Add:

src/app/api/realtime/stream/route.ts

This proxies frontend SSE to backend:

/api/realtime/stream -> http://host.docker.internal:8000/realtime/stream

This keeps auth/cookies consistent with the existing frontend proxy pattern.

⸻

useInboxRealtimeStream.ts

Inbox-specific hook.

On event:

customer_service.conversation.created
customer_service.message.created
customer_service.ai_reply.created
customer_service.workflow.*
customer_service.sla.updated

Do:

refreshInboxList()
refreshConversationData(selectedId) only if affected conversation is currently open
mark other affected conversation as unread
show operational badge

⸻

6. Frontend Behavior

When a new customer message arrives:

- conversation moves to top
- row becomes highlighted
- badge shows "New customer"
- unread count increases
- if selected conversation is open, message appears immediately

When workflow pauses for approval:

- row shows "Approval needed"
- right AI/workflow panel updates
- optional toast appears

When workflow succeeds:

- row shows "Workflow done"
- workflow execution card updates

When SLA is at risk:

- row shows "SLA at risk"
- row uses urgent color

⸻

7. V1 Implementation Plan

Step 1 — Backend foundation

Build:

app/realtime/schemas.py
app/realtime/hub.py
app/realtime/publisher.py
app/realtime/router.py

Add router to app/main.py.

Test:

- user connects to SSE
- publisher sends event
- only that user receives it
- heartbeat works

⸻

Step 2 — Customer-service publisher

Build:

app/domains/customer_service/realtime/events.py
app/domains/customer_service/realtime/publisher.py

Add helper methods:

publish_conversation_created(...)
publish_message_created(...)
publish_ai_reply_created(...)
publish_workflow_updated(...)
publish_approval_required(...)

⸻

Step 3 — Publish message events

Publish events from:

CustomerChatService.add_inbox_customer_message_for_chat_session
CustomerChatService.add_inbox_ai_message_for_chat_session
InboxService.add_message

⸻

Step 4 — Frontend SSE client

Build:

src/lib/realtime/client.ts
src/lib/realtime/events.ts
src/app/api/realtime/stream/route.ts

⸻

Step 5 — Inbox realtime hook

Build:

src/features/customer-service/inbox/hooks/useInboxRealtimeStream.ts

Replace or reduce polling.

⸻

Step 6 — Upgrade UI alerts

Use backend event type to show:

New customer
AI replied
Approval needed
Workflow failed
Workflow done
SLA at risk
Refund completed

⸻

8. Production Hardening Later

V1 can use in-memory hub.

Production should add:

Redis Pub/Sub
durable event table
event replay cursor
multi-worker support
rate limiting
tenant isolation tests
disconnect cleanup
heartbeat monitoring
browser notification permission

Final production shape:

domain service
  -> platform event store
  -> realtime publisher
  -> Redis pub/sub
  -> SSE clients
  -> frontend live UI

⸻

9. Why This Matters

This turns Tajeran Inbox from a static ticket list into a live operations center.

The agent should not refresh the page.

The agent should instantly see:

who needs help
what changed
what workflow is waiting
what Shopify action completed
what SLA is risky
what AI already handled

This is core product value, not only UI polish.

-------------------------

Tajeran Inbox Realtime UX Vision

Status: Planned
Priority: High
Depends on: Realtime Foundation
Layer: Customer Service UX

⸻

Vision

The inbox should not behave like a traditional ticket list.

It should behave like a live operations center.

An agent should immediately understand:

* what changed
* who needs attention
* what AI already handled
* what workflows are running
* where approvals are waiting
* what Shopify actions completed
* which conversations are becoming critical

without refreshing the page or reading long message previews.

The inbox should communicate state visually.

⸻

Design Principles

The inbox should optimize for:

* awareness
* speed
* clarity
* confidence

The UI should allow an experienced support agent to scan hundreds of conversations in seconds.

Text is secondary.

Visual state is primary.

⸻

Planned Improvements

⸻

1. Unread Conversation Count (Highest Priority)

Goal

Agents should immediately know which conversations require attention before opening them.

Instead of only highlighting a conversation row, every conversation should maintain an unread message count.

Example:

John Smith                          ● 3
Order #1052                         2m

Unread count disappears when:

* conversation is opened
* messages are marked as read

⸻

Benefits:

* immediate awareness
* prioritization
* no manual searching

⸻

2. Event-Based Visual States

Not every update is equally important.

The backend already knows what happened.

The inbox should reflect that visually.

⸻

New Customer

🟢 Green

Represents:

* first message
* first conversation

Purpose:

Draw attention to new customers entering the support queue.

⸻

Human Approval Required

🟣 Purple

Represents:

* workflow paused
* waiting for human approval

Purpose:

Immediate indication that AI is waiting for an agent.

⸻

Workflow Running

🟠 Orange

Represents:

* background workflow executing
* Shopify operation running

Purpose:

Shows that automation is actively processing the request.

⸻

SLA Risk

🔴 Red

Represents:

* SLA warning
* overdue ticket
* urgent customer

Purpose:

Highest visual priority.

⸻

AI Replied

🔵 Blue

Represents:

* AI generated response
* AI waiting for review

Purpose:

Lets agents immediately distinguish AI activity from customer activity.

⸻

Refund Completed

🟢 Success Green

Represents:

* refund completed
* shipping updated
* cancellation completed

Purpose:

Positive completion state.

⸻

The backend should publish event types.

The frontend should only render them.

⸻

3. Conversation Activity Icons

People recognize icons much faster than text.

Each conversation should display a primary activity icon.

Examples:

💬 Customer message

🤖 AI replied

⚙️ Workflow running

🛒 Shopify action

💰 Refund

🚚 Shipping

📦 Order lookup

👤 Human approval

⚠️ SLA warning

These icons become the visual language of the inbox.

⸻

4. Attention Animation

Animations should attract attention without becoming distracting.

Recommended behavior:

* animate only once
* fade into a static indicator
* never pulse forever

Continuous animations make the interface visually noisy after several hours of use.

⸻

5. Browser Notifications

If the inbox is not focused:

Display a browser notification.

Example:

New customer message
John Smith
"Where is my order?"

This matches user expectations from modern support platforms.

⸻

6. Notification Sound

Play a subtle notification sound when:

* customer sends a new message
* approval is required
* SLA becomes critical

The sound should be:

* short
* professional
* configurable
* disableable

⸻

7. Group Activity

When multiple messages arrive quickly:

Instead of displaying multiple independent notifications:

John Smith
3 new messages

This reduces visual noise while preserving urgency.

⸻

8. React to More Than Customer Messages

The inbox should eventually react to every important backend event.

Examples:

Customer message

AI reply

Workflow started

Workflow completed

Workflow failed

Workflow paused

Human approval required

Shopify refund completed

Order updated

Shipping changed

Ticket assigned

Tag added

SLA warning

Conversation closed

The inbox should become an event-driven workspace rather than a static message list.

⸻

Event-Driven Inbox Architecture

The inbox should subscribe to platform events.

The backend publishes:

customer_service.message.created
customer_service.ai_reply.created
workflow.started
workflow.completed
workflow.failed
workflow.paused
approval.required
shopify.refund.completed
shopify.shipping.updated
sla.warning
conversation.updated
ticket.assigned
conversation.closed

The frontend reacts to these events by updating the UI immediately.

No polling.

No manual refresh.

⸻

Long-Term Vision

Traditional support systems present a list of conversations.

Tajeran should present a live stream of operational activity.

Instead of asking:

“Which conversations exist?”

The inbox should answer:

“What changed that requires my attention?”

This transforms the inbox from a passive message list into an AI-native operations center.

The inbox becomes the primary interface between humans, AI agents, workflows, Shopify, and customers.

This aligns naturally with Tajeran’s platform architecture, where workflows, agents, events, jobs, and realtime infrastructure work together to provide a unified, event-driven customer support experience.

-------------------
Memory

Execution

Observation

Decision

Recovery

Learning

Events

Commerce

Human Collaboration

-----------------------
Tajeran

- Understand
    - Customer
    - Commerce
    - Conversation
    - Knowledge
    - Context
    - Intelligence
    - Recommendations

- Execute
    - AI
    - Human
    - Workflow
    - Commerce
    - Omnichannel
    - Routing
    - Macros

- Observe
    - Runtime
    - Timeline
    - State
    - Variables
    - Events
    - Metrics
    - Snapshots
    - Replay
    - Waits

- Improve
    - Evaluation
    - Quality
    - Analytics
    - Versions
    - Deployment

- Govern
    - Teams
    - Agents
    - Permissions
    - Event Subscriptions
    - Webhooks

------------------
- Week 1
- Execution Memory
Timeline

Snapshots

State

Replay

Diff
How execution memory works

How frontend should expose it

How customers think about it

Week 2

Decision System-Decision Center.
Human approval

Waits

Router

Interrupt

Resume

Week 3

Observation-Runtime Console.
Metrics

Runtime

Jobs

Events

SSE

Diagnostics

Week 4

Learning-Continuous Improvement.
Evaluation

Quality

Deployments

Versions

Regression

You see:
Conversation

↓

Understanding

↓

Reasoning

↓

Decision

↓

Execution

↓

Observation

↓

Learning

--------------------
My proposal is:

1. Understand

Everything that helps an agent or AI understand the situation.

2. Decide

Routing, approvals, recommendations, suggested actions, AI plans.

3. Execute

Replies, workflows, commerce actions, omnichannel operations.

4. Observe

Runtime, timeline, events, state, metrics, snapshots, replay.

5. Improve

Quality, evaluations, analytics, versions, deployments.

Every backend capability should belong to one of these workspaces.


----------------------------------------------------
I don’t actually want “Prompt creates workflow”

I want something more ambitious.

Prompt

↓

Creates Business Plan

↓

Business Plan becomes Workflow

↓

Workflow executes

↓

Verifier checks

↓

Repair fixes

↓

Result


1. Reasoning Architecture — define how Tajeran thinks about goals, tasks, constraints, and capabilities.
2. Planner Architecture — design the multi-stage planning pipeline instead of relying on a single prompt.
3. Workflow IR & Compiler — create an intermediate representation and compile it into your existing runtime DAG.
4. Verification & Repair — validate generated workflows, detect issues, and automatically repair when possible.
5. Learning & Optimization — use execution history and outcomes to improve future planning and workflow generation.
6. Frontend Experience — make React Flow a visual editor for AI-generated workflows and provide transparent reasoning, execution traces, and opportunities for users to intervene.

I think your runtime becomes incredibly valuable

The more I study it, the more I think your runtime is the part that would be hardest for another company to recreate.

Planning is difficult.

Execution is much harder.

Durable execution.

Replay.

Resume.

Approvals.

Idempotency.

Persistence.

Timeline.

Those take years to mature.

You already have them.

### I want it to become:

An execution operating system that understands goals, reasons about them, compiles them into reliable workflows, executes them durably, verifies the outcome,
repairs failures when possible, and continuously improves from experience.
Tajeran should become the platform that turns human intent into verified real-world outcomes through transparent reasoning, deterministic compilation, and durable execution.