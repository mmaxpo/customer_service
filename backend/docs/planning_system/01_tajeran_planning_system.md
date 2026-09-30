# Tajeran Planning System
**Version:** 0.1 (Architecture Draft)

---

# Vision

Tajeran is **not** a workflow builder.

It is **not** an AI chat application.

It is **not** an agent framework.

Those are capabilities.

The actual product is a **Business Execution Engine** capable of transforming an ambiguous business goal into a verified business outcome.

The long-term objective is:

```
User Goal

↓

Understand

↓

Plan

↓

Build Execution Strategy

↓

Execute

↓

Verify

↓

Repair

↓

Return Result
```

Everything inside Tajeran should eventually exist to improve one stage of this pipeline.

---

# The Philosophy

Traditional workflow systems require humans to design execution.

```
Human
↓

Design Workflow

↓

Execute Workflow
```

Traditional chat systems require LLM reasoning every request.

```
Prompt

↓

LLM

↓

Answer
```

Tajeran combines both.

```
Prompt

↓

Planning Layer

↓

Execution Runtime

↓

Verification

↓

Learning
```

The LLM becomes one reasoning component—not the system itself.

The system owns execution.

---

# High-Level Architecture

```
                User Prompt
                     │
                     ▼
          Intent Understanding
                     │
                     ▼
              Goal Extraction
                     │
                     ▼
          Business Task Graph
                     │
                     ▼
          Capability Planning
                     │
                     ▼
             Workflow Compiler
                     │
                     ▼
               Workflow IR
                     │
                     ▼
            Runtime Execution
                     │
                     ▼
               Verification
                     │
          ┌──────────┴──────────┐
          │                     │
     Success                 Failed
          │                     │
          ▼                     ▼
      Final Result         Repair Planner
                                │
                                ▼
                         Continue Execution
```

---

# Planning Pipeline

Every request eventually becomes:

```
User Prompt

↓

Intent

↓

Goal

↓

Task Graph

↓

Execution Plan

↓

Workflow

↓

Execution

↓

Verification

↓

Result
```

---

# Stage 1 — Intent Understanding

Purpose:

Understand what the user is trying to accomplish.

Not:

"What did the user say?"

Instead:

"What business outcome is the user asking for?"

Example

Prompt

```
Customer wants a refund because the product arrived damaged.
```

Intent Object

```json
{
  "domain": "customer_service",
  "intent": "refund_request",
  "confidence": 0.97
}
```

The Intent layer never creates workflows.

It only understands.

---

# Stage 2 — Goal Extraction

Intent is still too small.

We need the actual goal.

Example

```
Goal:
Resolve customer's damaged-product issue.
```

Goal Object

```json
{
    "goal_id":"resolve_refund_request",
    "priority":"high",
    "success_definition":[
        "Customer receives correct response",
        "Refund policy checked",
        "Refund executed or recommended",
        "Conversation updated"
    ]
}
```

Notice:

Goals define outcomes.

Not implementation.

---

# Stage 3 — Business Task Graph

This is probably the most important object in Tajeran.

It answers:

"What work must happen?"

Example

```
Resolve Refund

├── Read conversation
├── Read customer
├── Read order
├── Check refund policy
├── Decide eligibility
├── Generate reply
└── Update conversation
```

Nothing here references:

- runtime
- DAG
- workflow
- nodes
- tools

Only business work.

---

# Stage 4 — Capability Planning

Now the planner maps business tasks to platform capabilities.

Example

```
Read Order
↓

shopify.get_order
```

```
Read Conversation
↓

conversation.load
```

```
Check Policy
↓

knowledge.search
```

```
Generate Reply
↓

agent.custom
```

Business Tasks become executable capabilities.

---

# Stage 5 — Workflow Compiler

The planner still has not produced a runtime workflow.

Instead it has produced:

Business Graph

↓

Compiler

↓

Workflow IR

The compiler is deterministic.

No LLM decisions should happen here.

---

# Stage 6 — Workflow IR

Workflow IR (Intermediate Representation)

This becomes the contract between:

Planning

and

Runtime

Example

```json
{
    "steps":[
        {
            "type":"shopify.get_order"
        },
        {
            "type":"knowledge.search"
        },
        {
            "type":"agent.custom"
        }
    ]
}
```

This representation is runtime-independent.

---

# Stage 7 — Runtime Compilation

Workflow IR

↓

Runtime DAG

↓

Execution Engine

This is where today's runtime already excels.

Responsibilities:

- scheduling
- persistence
- waits
- resume
- replay
- retries
- approvals
- events
- execution
- state

Most of this layer already exists.

---

# Stage 8 — Verification

Execution success is not enough.

Need to answer:

Did we actually achieve the goal?

Example

Execution finished.

Verification checks:

```
✓ refund eligibility evaluated

✓ customer reply exists

✓ conversation updated

✓ required approval completed
```

If all pass:

Goal complete.

---

# Stage 9 — Repair

If verification fails:

Planner creates only the missing work.

Example

```
Refund created

×

Customer never notified
```

Repair Graph

```
Notify Customer
```

instead of rebuilding everything.

---

# Stage 10 — Learning

Eventually Tajeran should improve planning itself.

Learning may include:

- workflow success rate
- verification failures
- repair frequency
- execution latency
- tool reliability
- token efficiency
- planner quality

Learning changes future planning.

Not runtime.

---

# Component Responsibilities

| Component | Responsibility |
|------------|----------------|
| Intent Engine | Understand request |
| Goal Engine | Define desired outcome |
| Planner | Build Business Task Graph |
| Capability Resolver | Match business tasks to platform capabilities |
| Compiler | Convert Business Graph into Workflow IR |
| Runtime Compiler | Convert IR into Runtime DAG |
| Runtime Engine | Execute workflow |
| Verification Engine | Confirm success |
| Repair Engine | Build incremental repair workflow |
| Learning Engine | Improve future planning |

---

# Existing Tajeran Status

## Runtime Engine

Estimated maturity:

**95%**

Already contains:

- durable execution
- workflow persistence
- DAG execution
- state management
- event sourcing
- waits
- retries
- approvals
- replay
- cancellation
- idempotency

---

## Agent Runtime

Estimated maturity:

**90%**

Already contains:

- reasoning
- tool calling
- approvals
- memory
- events
- persistence
- resume
- usage tracking

---

## Planning Layer

Estimated maturity:

**15%**

Mostly missing.

Needs:

- Intent Engine
- Goal Engine
- Planner
- Capability Resolver
- Workflow Compiler
- Verification Planner
- Repair Planner

---

# Design Principles

1. Planning should be deterministic wherever possible.

2. LLMs should propose—not own—the architecture.

3. Runtime should execute—not think.

4. Verification should validate outcomes—not merely execution.

5. Repair should modify only failed parts.

6. Business tasks should remain independent from runtime implementation.

7. Workflow IR should be stable even if runtime evolves.

8. Capabilities should be reusable across every Tajeran product.

---

# Long-Term Vision

Eventually every Tajeran product should follow exactly the same pipeline.

```
User Goal

↓

Intent

↓

Goal

↓

Business Task Graph

↓

Capability Plan

↓

Workflow IR

↓

Runtime DAG

↓

Execution

↓

Verification

↓

Repair

↓

Result
```

Customer Service.

Sales.

HR.

IT Automation.

Security.

PAM.

ERP.

Internal AI.

Future products should differ only in their capabilities—not in their planning architecture.

---

# Architecture North Star

The runtime should never need to know *why* work exists.

The planner should never need to know *how* work executes.

This separation is the foundation of a scalable, multi-product, AI-native execution platform.