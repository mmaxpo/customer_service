# Stage 01 — Tajeran Current Backend Mapping to Target AI Operating System

## Purpose

This document maps the current Tajeran backend to the target architecture:

User Prompt  
→ Intent Extraction  
→ Planning System  
→ Business Task Graph  
→ Capability Registry  
→ Capability Resolver  
→ Workflow IR  
→ Workflow Compiler  
→ Execution Runtime  
→ Agent Runtime  
→ Verification System  
→ Self Repair System  
→ Result

The goal is to identify what already exists, what is partial, and what is missing.

---

# 1. Current Backend Reality

Tajeran already has a strong execution foundation.

The backend is not just a customer-service app.

It is already close to a custom agentic orchestration framework.

Current strong areas:

- Durable workflow runtime
- DAG execution
- Parallel node execution
- Runtime state
- Runtime events
- Timeline
- Snapshots
- Resume
- Human approval
- Waits
- Jobs
- Agent runtime
- Tool execution
- Shopify actions
- Knowledge search
- Customer-service workflow templates
- Omnichannel/event infrastructure

The missing part is not execution.

The missing part is the intelligent planning layer above execution.

---

# 2. Target Architecture Mapping

## 2.1 User Prompt

Current status: partially exists

Today user messages can enter through:

- `/workflows_route/run`
- Customer chat
- Agent runtime
- Customer service conversation workflow
- Workflow templates

But there is not yet a formal universal prompt entrypoint like:

```text
POST /planning/run
```

or

```text
POST /ai-tasks/run
```

Needed:

- One top-level endpoint that accepts a natural language task.
- It should not directly execute.
- It should start planning.

Status: 🟡 Partial

---

## 2.2 Intent Extraction

Current status: weak / scattered

Some intent-like behavior exists in customer service:

- triage
- message classifier
- conversation intelligence
- suggested actions
- routing policies

But there is not yet a universal intent extraction layer for arbitrary business tasks.

Needed:

- Intent schema
- Intent extractor
- Confidence score
- Domain detection
- Required entities
- Missing information detection

Example output:

```json
{
  "domain": "customer_service",
  "intent": "refund_request",
  "entities": {
    "order_ref": "#1001"
  },
  "confidence": 0.91,
  "missing_fields": []
}
```

Status: 🟡 Partial

---

## 2.3 Planning System

Current status: mostly missing

The backend currently executes workflows very well, but it does not yet create workflows from a user prompt.

Missing:

- Planner service
- Planner schema
- Plan validation
- Planner prompt policy
- Planner output contract
- Planner event logging

Needed output:

```json
{
  "goal": "Handle refund request",
  "tasks": [
    "read_conversation",
    "read_order",
    "check_policy",
    "decide_refund",
    "generate_reply"
  ]
}
```

Status: ❌ Missing

---

## 2.4 Business Task Graph

Current status: missing as formal layer

The runtime already executes DAGs.

But there is no separate business-level task graph.

Today, workflows are already close to runtime node graphs.

Needed:

- BusinessTask model
- BusinessTaskGraph model
- Dependencies
- Task purpose
- Inputs
- Outputs
- Risk level
- Capability requirements

Example:

```json
{
  "tasks": [
    {
      "id": "task_read_order",
      "goal": "Read Shopify order",
      "depends_on": [],
      "required_capability": "commerce.order.read"
    }
  ]
}
```

Status: ❌ Missing

---

## 2.5 Capability Registry

Current status: implicit but not formal

This is one of the biggest opportunities.

Tajeran already has many capabilities:

- `trigger.message`
- `response`
- `set.variable`
- `router.rules`
- `router.llm`
- `join.all`
- `human.approval`
- `wait.time`
- `wait.event`
- `subworkflow.call`
- `agent.custom`
- `knowledge.search`
- `shopify.get_order`
- `shopify.action`
- `platform.job`
- `web.search`
- `web.fetch_extract`
- `customer.chat.reply`

But they are not exposed as a formal planning registry.

Needed:

- Capability schema
- Capability metadata
- Cost
- latency
- required inputs
- outputs
- side effect flag
- approval requirement
- runtime node mapping

Status: 🟡 Partial foundation, formal registry missing

---

## 2.6 Capability Resolver

Current status: missing

The planner currently has no service that says:

```text
Task: refund customer
→ capability: shopify.refund
```

Needed:

- Semantic capability search
- Deterministic filtering
- Permission filtering
- Domain filtering
- Tool availability filtering
- Capability ranking

Status: ❌ Missing

---

## 2.7 Workflow IR

Current status: implicit

Today the system accepts runtime workflow JSON:

```json
{
  "nodes": [],
  "edges": []
}
```

But this is not a clean intermediate representation.

Needed:

- A planner-friendly Workflow IR
- Separate from React Flow
- Separate from runtime DAG
- Stable contract between planning and compiler

Status: 🟡 Implicit, not formal

---

## 2.8 Workflow Compiler

Current status: mostly missing

Today frontend or templates create runtime workflow JSON directly.

Needed:

```text
Business Task Graph
→ Capability selections
→ Workflow IR
→ Runtime workflow nodes/edges
```

Compiler responsibilities:

- Add trigger node
- Add response node
- Create runtime nodes
- Create edges
- Inject approvals
- Inject joins
- Inject token budgets
- Inject retries
- Validate executable graph

Status: ❌ Missing

---

## 2.9 Execution Runtime

Current status: very strong

This is the strongest layer.

Already exists:

- `execute_workflow_dag`
- Runtime context
- DAG execution
- Parallel execution
- node events
- run state
- persistence
- snapshots
- waits
- approvals
- resume
- timeline
- SSE
- replay safety
- idempotency

Manual tests confirmed:

- Simple workflow works
- Human approval pause/resume works
- Router rules works
- Branch skip works
- Parallel execution works
- Join works
- Agent custom workflow works

Status: ✅ Very strong, around 95%

---

## 2.10 Agent Runtime

Current status: strong

Already exists:

- `AgentRunner`
- tool loop
- LLM calls
- tool execution
- approval pause
- resume after approval
- event recorder
- state store
- token budget
- usage tracking
- `agent.custom` node

Manual tests confirmed:

- Standalone agent works after model/schema fix
- Agent custom workflow works
- Agent output can be saved into workflow state
- Agent events appear inside node metadata

Important gap found:

- `AgentRunEvent.workflow_run_id` model mismatch caused DB error.
- Removing that stale model column fixed persistence mismatch.

Status: ✅ Strong, around 85–90%

---

## 2.11 Verification System

Current status: low

Some related foundations exist:

- workflow quality
- evaluations
- regression checks
- reply quality
- quality reviews
- runtime events
- structured outputs

But there is no universal verification engine.

Needed:

- Task verifier
- Workflow verifier
- Agent output verifier
- Policy verifier
- Confidence score
- Failure reasons
- Accept/reject contract

Status: 🟡 Foundation exists, verification layer missing

---

## 2.12 Self Repair System

Current status: low

Some foundations exist:

- retry
- replay
- resume
- jobs recovery
- dead letters
- workflow waits
- snapshots

But intelligent repair does not yet exist.

Needed:

- repair planner
- failure classifier
- retry strategy selector
- alternative capability selector
- workflow mutation
- verification-driven repair loop

Status: 🟡 Infrastructure exists, intelligence missing

---

# 3. Key Insight

Tajeran has built the hardest low-level part first.

Most AI companies start with:

```text
Prompt → Agent
```

Then they struggle with:

- persistence
- replay
- events
- approvals
- state
- recovery
- idempotency
- production execution

Tajeran already has those.

So the next phase should not be rebuilding runtime.

The next phase should be building:

```text
Prompt → Plan → Compile → Execute → Verify → Repair
```

above the existing runtime.

---

# 4. Current Backend Score

| Layer | Current Status |
|---|---|
| Execution Runtime | ✅ 95% |
| Agent Runtime | ✅ 85–90% |
| Customer Service Domain | ✅ 80–90% |
| Jobs / Events / Waits | ✅ 85–95% |
| Capability Inventory | ✅ 80% |
| Formal Capability Registry | ❌ 10% |
| Planning System | ❌ 10–20% |
| Business Task Graph | ❌ 10% |
| Workflow IR | 🟡 20% |
| Workflow Compiler | ❌ 10% |
| Verification System | 🟡 20% |
| Self Repair System | 🟡 15% |

---

# 5. Recommended Implementation Order

Do not start with frontend.

Do not start with React Flow.

Do not start with a huge planner.

Start with backend contracts.

Recommended order:

1. Capability Registry
2. Business Task Graph schema
3. Workflow IR schema
4. Deterministic Workflow Compiler
5. Simple planner that creates task graph
6. Planner validation
7. Verification system
8. Repair system
9. Frontend prompt-to-workflow UI

---

# 6. First Real Backend Build Target

The first production-grade milestone should be:

```text
User prompt:
"Create a workflow that replies to damaged item refund requests."

↓

Planner creates Business Task Graph

↓

Capability Resolver selects:
- trigger.message
- agent.custom
- response

↓

Compiler creates runtime workflow

↓

Runtime executes it
```

This should be intentionally small.

Not all capabilities.

Not all business domains.

One vertical slice.

---

# 7. Why This First Slice Matters

This proves the whole future system:

```text
Prompt

↓

Plan

↓

Compile

↓

Run

↓

Events

↓

State

↓

Answer
```

Once this works, Tajeran has the foundation for prompt-created workflows.

Then the system can grow capability by capability.

---

# 8. Next Investigation Stage

The next document should be:

```text
Stage 02 — Capability Inventory Mapping
```

Purpose:

Map every current backend node/service/tool into a formal capability list.

This becomes the seed for the real Capability Registry.

That document should identify:

- capability id
- business name
- runtime node
- inputs
- outputs
- side effect
- approval required
- readiness level
- source file

This is the most important next step before implementation.