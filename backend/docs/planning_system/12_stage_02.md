# Stage 02 — Capability Inventory Mapping

Version: 0.1

---

# Purpose

This document inventories every business capability currently implemented inside Tajeran.

This is **not** a node inventory.

This is **not** a file inventory.

It is a business capability inventory.

The goal is to answer one question:

> **"What can Tajeran actually do today?"**

This inventory becomes the foundation for the Capability Registry.

---

# Capability Definition

A capability is:

> One reusable business action that the platform knows how to perform.

A capability is NOT

- a Python class
- a runtime node
- a REST endpoint
- a database model

One capability may use many runtime nodes.

One runtime node may implement multiple capabilities.

---

# Capability Readiness Levels

| Level | Meaning |
|--------|----------|
| A | Production Ready |
| B | Production with minor improvements |
| C | Functional but needs redesign |
| D | Prototype |
| E | Planned only |

---

# Capability Categories

Current investigation shows Tajeran capabilities naturally fall into these domains.

```
Core Runtime

AI

Commerce

Customer Service

Knowledge

Communication

Workflow

Platform

Human

Infrastructure
```

---

# 1. Core Runtime Capabilities

---

## Execute Workflow

Capability ID

```
workflow.execute
```

Purpose

Execute an entire workflow DAG.

Current Runtime

```
execute_workflow_dag()
```

Inputs

- workflow
- input
- runtime context

Outputs

- workflow state
- answer
- events

Readiness

✅ A

---

## Resume Workflow

Capability

```
workflow.resume
```

Purpose

Resume paused workflow.

Readiness

✅ A

---

## Pause Workflow

Capability

```
workflow.pause
```

Purpose

Pause execution safely.

Readiness

✅ A

---

## Cancel Workflow

Capability

```
workflow.cancel
```

Purpose

Gracefully cancel workflow.

Readiness

✅ A

---

## Replay Workflow

Capability

```
workflow.replay
```

Purpose

Replay execution safely.

Readiness

✅ A

---

## Parallel Execution

Capability

```
workflow.parallel
```

Purpose

Execute independent nodes simultaneously.

Readiness

✅ A

---

## Join Parallel Branches

Capability

```
workflow.join
```

Purpose

Synchronize multiple execution branches.

Runtime Node

```
join.all
```

Readiness

✅ A

---

# 2. AI Capabilities

---

## Execute Agent

Capability

```
agent.execute
```

Runtime

```
AgentRunner
```

Readiness

✅ A

---

## Resume Agent

Capability

```
agent.resume
```

Readiness

✅ A

---

## Pause Agent

Capability

```
agent.pause
```

Readiness

✅ A

---

## Tool Calling

Capability

```
agent.tool_call
```

Purpose

Execute approved runtime tools.

Readiness

✅ A

---

## Multi-Step Reasoning

Capability

```
agent.reason
```

Purpose

Perform iterative reasoning.

Readiness

✅ A

---

## Token Budgeting

Capability

```
agent.token_budget
```

Readiness

✅ A

---

## Reasoning Budget

Capability

```
agent.reasoning_budget
```

Readiness

✅ A

---

## Agent Events

Capability

```
agent.events
```

Purpose

Publish execution timeline.

Readiness

✅ A

---

# 3. Customer Service

---

## Generate Reply

Capability

```
customer.reply.generate
```

Current

Uses

```
agent.custom
```

Readiness

✅ B

---

## Conversation Timeline

Capability

```
conversation.timeline
```

Readiness

✅ A

---

## Conversation Search

Capability

```
conversation.search
```

Readiness

✅ B

---

## Customer Lookup

Capability

```
customer.lookup
```

Readiness

✅ B

---

## Suggested Actions

Capability

```
conversation.suggestions
```

Readiness

✅ B

---

## Conversation Classification

Capability

```
conversation.classify
```

Readiness

✅ B

---

## Routing

Capability

```
conversation.route
```

Readiness

✅ B

---

## Ticket Management

Capability

```
ticket.manage
```

Readiness

✅ B

---

## SLA Tracking

Capability

```
ticket.sla
```

Readiness

✅ B

---

# 4. Commerce (Shopify)

---

## Read Order

Capability

```
commerce.order.read
```

Readiness

✅ A

---

## Refund Order

Capability

```
commerce.refund.create
```

Approval Required

YES

Readiness

✅ A

---

## Cancel Order

Capability

```
commerce.order.cancel
```

Approval Required

YES

Readiness

✅ A

---

## Update Shipping Address

Capability

```
commerce.shipping.update
```

Readiness

✅ A

---

## Shipping Status

Capability

```
commerce.shipping.status
```

Readiness

✅ A

---

## Reship Order

Capability

```
commerce.order.reship
```

Readiness

✅ A

---

# 5. Knowledge

---

## Knowledge Search

Capability

```
knowledge.search
```

Readiness

✅ A

---

## Knowledge Retrieval

Capability

```
knowledge.retrieve
```

Readiness

✅ B

---

## Knowledge Ingest

Capability

```
knowledge.ingest
```

Readiness

✅ B

---

# 6. Human Interaction

---

## Human Approval

Capability

```
human.approval
```

Readiness

✅ A

---

## Wait For Approval

Capability

```
human.wait
```

Readiness

✅ A

---

# 7. Workflow Control

---

## Wait Time

Capability

```
workflow.wait.time
```

Readiness

✅ A

---

## Wait Event

Capability

```
workflow.wait.event
```

Readiness

✅ A

---

## Router Rules

Capability

```
workflow.router.rules
```

Readiness

✅ A

---

## Router LLM

Capability

```
workflow.router.llm
```

Readiness

🟡 B

---

## Set Variable

Capability

```
workflow.variable.set
```

Readiness

✅ A

---

## Trigger Message

Capability

```
workflow.trigger.message
```

Readiness

✅ A

---

## Response

Capability

```
workflow.response
```

Readiness

✅ A

---

## Subworkflow

Capability

```
workflow.subworkflow
```

Readiness

🟡 B

---

# 8. Platform

---

## Platform Job

Capability

```
platform.job.enqueue
```

Readiness

✅ A

---

## Event Publishing

Capability

```
platform.event.publish
```

Readiness

✅ A

---

## Timeline

Capability

```
platform.timeline
```

Readiness

✅ A

---

## Metrics

Capability

```
platform.metrics
```

Readiness

🟡 B

---

# 9. Web Intelligence

---

## Web Search

Capability

```
web.search
```

Readiness

🟡 B

---

## Fetch Web Page

Capability

```
web.fetch
```

Readiness

🟡 B

---

# 10. Infrastructure

---

## State Persistence

Capability

```
runtime.state.persistence
```

Readiness

✅ A

---

## Event Persistence

Capability

```
runtime.event.persistence
```

Readiness

✅ A

---

## Snapshot

Capability

```
runtime.snapshot
```

Readiness

✅ A

---

## Replay

Capability

```
runtime.replay
```

Readiness

✅ A

---

## Resume

Capability

```
runtime.resume
```

Readiness

✅ A

---

## Retry

Capability

```
runtime.retry
```

Readiness

✅ A

---

## Idempotency

Capability

```
runtime.idempotency
```

Readiness

✅ A

---

# Capability Statistics

Approximate inventory

| Domain | Count |
|----------|------:|
| Runtime | 12 |
| AI | 8 |
| Customer Service | 8 |
| Commerce | 6 |
| Knowledge | 3 |
| Human | 2 |
| Workflow | 9 |
| Platform | 4 |
| Web | 2 |
| Infrastructure | 7 |

Estimated current capability inventory

≈61 business capabilities

This number will likely exceed 100 after a full repository investigation.

---

# Capability Quality

Production Ready (A)

≈40

Production (B)

≈18

Prototype (C)

≈3

Planned

many

---

# Key Observation

The backend already contains a rich capability ecosystem.

The planner does **not** need new business logic.

It needs a way to **discover**, **rank**, and **compose** these existing capabilities.

This dramatically reduces the amount of new implementation required for prompt-driven workflow generation.

---

# Next Investigation

Stage 03

Capability Dependency Graph

Instead of asking

"What capabilities exist?"

we ask

"How do capabilities depend on each other?"

This document will reveal:

- prerequisite capabilities
- shared business objects
- reusable execution patterns
- common workflow motifs
- opportunities for automatic workflow composition

This is the bridge between a flat capability catalog and an intelligent planner.
