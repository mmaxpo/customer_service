# Stage 21 — Planner Memory & Knowledge Architecture

Version: 0.1

---

# Purpose

The Planner Memory Architecture defines **everything Tajeran knows** and **how it remembers**.

This is one of the most important architectural layers in the entire platform.

Without memory:

```
Planner

↓

Starts from zero

Every Task
```

With proper memory:

```
Planner

↓

Uses Experience

↓

Uses Business Knowledge

↓

Uses Previous Work

↓

Uses Organizational Intelligence

↓

Creates Better Plans
```

The planner becomes an expert instead of a beginner.

---

# Philosophy

One of the biggest mistakes in AI systems is putting everything into one vector database.

Eventually everything becomes:

```
Embeddings

+

Random Documents

+

Conversation History

+

Logs

+

Prompts
```

Then the planner has no idea what information is authoritative.

Tajeran should separate memory by responsibility.

Just like software architecture separates services.

---

# Memory Pyramid

```
                    User Prompt
                         │
                         ▼
                Working Memory
                         │
                         ▼
              Planning Memory
                         │
                         ▼
             Business Knowledge
                         │
                         ▼
          Organizational Knowledge
                         │
                         ▼
            Global AI Knowledge
```

Each layer has a different purpose.

---

# Memory Layers

There are seven independent memory systems.

```
1. Working Memory

2. Execution Memory

3. Planning Memory

4. Business Memory

5. Organizational Memory

6. Knowledge Memory

7. Learning Memory
```

Each one has different lifecycle rules.

---

# 1. Working Memory

Lifetime:

```
One Execution
```

Contains

```
Variables

Current Results

Tool Outputs

Intermediate Decisions

Context Window

Current Task Graph
```

Destroyed after execution.

Exactly like RAM.

---

# Example

```
Customer

↓

Refund Request

↓

Order Lookup

↓

Policy Result

↓

Refund Decision
```

Everything lives only during execution.

---

# 2. Execution Memory

Purpose

Remember exactly what happened.

Stores

```
Events

Node Outputs

Tool Calls

Costs

Latency

Execution Graph

Errors
```

Never edited.

Append-only.

Like Git history.

---

# Example

```
Execution #5831

↓

Read Order

↓

Refund

↓

Notify Customer
```

Always reproducible.

---

# 3. Planning Memory

This is the planner's brain.

Stores

```
Planning Strategies

Task Graphs

Successful Plans

Failed Plans

Planner Confidence

Plan Statistics
```

Planner consults this before planning.

---

# Example

Prompt

```
Refund damaged order
```

Planner remembers

```
Last 12,000 successful refund plans.
```

Instead of starting from zero.

---

# 4. Business Memory

Every company has different rules.

Business memory stores

```
Refund Policies

Shipping Rules

Tone of Voice

Working Hours

Approval Rules

Roles

Brand Personality

Products

Business Preferences
```

Company-specific.

---

# Example

Merchant A

```
Refund

without approval

under $50
```

Merchant B

```
Manager Approval

always
```

Planner behaves differently.

---

# 5. Organizational Memory

This is larger than one business.

Contains

```
Best Practices

Workflow Templates

Playbooks

Industry Standards

Common Processes
```

Shared knowledge.

---

# Example

Customer Support

```
Refund Flow

Replacement Flow

Escalation Flow

Subscription Cancellation
```

Available to all merchants.

---

# 6. Knowledge Memory

This answers questions.

Usually RAG.

Contains

```
Documentation

Policies

Articles

FAQs

Manuals

Knowledge Base
```

Planner queries it when facts are needed.

---

# Difference

Knowledge Memory

answers

```
What is true?
```

Planning Memory

answers

```
What should I do?
```

Different responsibilities.

---

# 7. Learning Memory

Stores

```
Lessons

Patterns

Scores

Optimizations

Failures

Repairs

Successful Strategies
```

Planner continuously improves.

---

# Memory Relationships

```
Working Memory

↓

Execution Memory

↓

Learning Memory

↓

Planning Memory
```

Planning evolves through experience.

---

# Memory Lifetime

| Memory | Lifetime |
|----------|------------|
| Working | Minutes |
| Execution | Forever |
| Planning | Long-term |
| Business | Long-term |
| Organization | Long-term |
| Knowledge | Versioned |
| Learning | Growing |

---

# Planner Retrieval Pipeline

Planner does NOT query everything.

Instead

```
Prompt

↓

Intent

↓

Determine Needed Memories

↓

Retrieve

↓

Plan
```

Much cheaper.

Much faster.

---

# Memory Routing

Planner first decides

```
Need Business Policy?

Need Documentation?

Need Previous Plans?

Need Customer History?

Need Learning?
```

Only retrieve what is necessary.

---

# Example

Prompt

```
Refund Order
```

Planner retrieves

```
Business Policy

+

Refund Workflow Template

+

Previous Successful Plans
```

No need to search product manuals.

---

# Memory Isolation

Merchant A

must NEVER access

Merchant B

Planning memory.

Everything is tenant isolated.

---

# Namespaces

Suggested

```
tenant_id

organization_id

planner_namespace

knowledge_namespace

workflow_namespace

customer_namespace
```

Everything isolated.

---

# Memory Indexes

Planning Memory

indexed by

```
Intent

Task Type

Industry

Capabilities

Complexity
```

Business Memory

indexed by

```
Company

Policy

Department

Role
```

Learning

indexed by

```
Strategy

Failure Type

Repair Type

Confidence
```

---

# Planner Cache

Frequently used plans should be cached.

Example

```
Refund

Cancel Order

Track Shipment
```

Planner can retrieve instantly.

---

# Versioning

Everything should be versioned.

```
Business Policies

Workflow Templates

Knowledge

Planner Strategies

Lessons
```

Nothing mutable without history.

---

# Context Assembly

Planner constructs context dynamically.

```
Prompt

↓

Business Memory

↓

Knowledge

↓

Planning Memory

↓

Learning

↓

Execution Context

↓

LLM
```

Instead of massive prompts.

---

# Memory Budget

Planner has limited context.

Need ranking.

Ranking based on

```
Relevance

Freshness

Confidence

Importance

Business Priority
```

---

# Planner Memory Objects

Every memory object has

```json
{
    "id": "...",

    "type":"planning",

    "confidence":0.98,

    "tenant_id":"...",

    "created_at":"...",

    "updated_at":"...",

    "source":"learning",

    "tags":[]
}
```

Unified metadata.

---

# Planner Never Reads Raw Logs

Bad

```
Planner

↓

100,000 events
```

Good

```
Planner

↓

Summarized Lessons
```

Execution logs feed learning.

Learning feeds planning.

---

# Suggested Backend Structure

```
app/planner/memory/

    working/

    planning/

    execution/

    business/

    organization/

    learning/

    knowledge/

    retrieval/

    ranking/

    cache/
```

---

# APIs

```python
memory.retrieve(

    intent,

    business,

    task

)
```

Returns

```
PlannerContext
```

---

# PlannerContext

Example

```python
PlannerContext(

    business_rules=[],

    workflow_templates=[],

    previous_plans=[],

    lessons=[],

    knowledge=[],

    customer_history=[],

    planner_statistics=[]

)
```

Planner receives structured context instead of random documents.

---

# Current Tajeran Mapping

Already Exists

✅ Workflow Runtime

✅ Event Store

✅ Workflow Persistence

✅ Agent State

✅ Knowledge Search

✅ Workflow Templates

✅ Customer Data

Partially Exists

🟡 Runtime State

🟡 Context Builder

🟡 Agent Metadata

Missing

❌ Planner Memory

❌ Planning Store

❌ Learning Store

❌ Business Rule Store

❌ Organizational Memory

❌ Retrieval Engine

❌ Context Ranking

---

# Target Architecture

```
User Prompt

↓

Intent Engine

↓

Memory Router

↓

Planner Context Builder

↓

Planner

↓

Task Graph

↓

Workflow Compiler

↓

Execution Runtime

↓

Verification

↓

Repair

↓

Learning

↓

Memory Update
```

Every component has exactly one responsibility.

---

# MVP

Version 1

- Planner memory store
- Business rule store
- Workflow template store
- Context builder
- Retrieval engine
- Ranking engine

Learning integration comes afterward.

---

# Current Readiness

Execution Runtime

★★★★★

Planning Runtime

★★★★☆

Knowledge Layer

★★★★☆

Planner Memory

★☆☆☆☆

Learning Memory

☆☆☆☆☆

Organizational Intelligence

☆☆☆☆☆

---

# Final Architecture Status

After Stage 21, the conceptual architecture for Tajeran's autonomous planning system is complete.

The next phase is no longer architecture.

It becomes engineering.

---

# Phase 2 — Production Implementation Roadmap

The implementation phase will transform the architecture into production code.

Major implementation tracks:

1. Planner Core
2. Intent Engine
3. Capability Registry
4. Task Graph Generator
5. Workflow Compiler
6. Verification Engine
7. Repair Planner
8. Learning Engine
9. Planner Memory
10. Frontend Planner Studio

At this point, your existing backend already provides approximately **80–90% of the execution infrastructure**. The remaining work is primarily to build the intelligence layer that sits above it rather than replacing the runtime you've already engineered.