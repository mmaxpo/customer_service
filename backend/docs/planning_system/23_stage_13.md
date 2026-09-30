# Stage 13 — Workflow Compiler

Version: 0.1

---

# Purpose

The Workflow Compiler is responsible for transforming a validated Workflow IR into an executable Runtime Workflow.

It is the bridge between planning and execution.

```
Planning Graph

↓

Workflow IR

↓

Workflow Compiler

↓

Runtime DAG

↓

Execution Engine
```

The compiler does **not think**.

The planner thinks.

The compiler translates.

---

# Philosophy

Planner answers:

> What should happen?

Compiler answers:

> How does our runtime execute it?

Execution answers:

> Run it.

Keeping these separate makes the system understandable, testable, and replaceable.

---

# Responsibilities

The Workflow Compiler is responsible for:

- translating capabilities into runtime nodes
- inserting runtime edges
- assigning execution order
- inserting checkpoints
- inserting approval nodes
- inserting verification nodes
- inserting repair paths
- resolving provider implementations
- producing valid Runtime DAG JSON

The compiler is **not** responsible for:

- understanding user prompts
- deciding business logic
- selecting goals
- evaluating quality
- executing nodes

---

# Input

Workflow IR

Example

```json
{
  "steps":[

    {
      "id":"read_order",
      "type":"capability",
      "capability":"commerce.order.read"
    },

    {
      "id":"reply",
      "type":"result"
    }

  ]
}
```

---

# Output

Existing Runtime DAG

Example

```json
{
  "nodes":[

      {
         "id":"read_order",
         "nodeType":"shopify.get_order"
      },

      {
         "id":"reply",
         "nodeType":"agent.custom"
      }

  ],

  "edges":[]
}
```

Exactly what your runtime already executes.

---

# Compiler Pipeline

```
Workflow IR

↓

Validate

↓

Resolve Capabilities

↓

Expand Policies

↓

Optimize

↓

Generate Runtime Nodes

↓

Generate Runtime Edges

↓

Validate DAG

↓

Return Runtime Workflow
```

---

# Phase 1 — Validation

Compiler refuses invalid IR.

Checks:

Missing inputs

Duplicate outputs

Unknown capability

Impossible dependency

Cycles

Unknown policy

Unknown verification

Invalid approval chain

---

# Phase 2 — Capability Resolution

This is where business abstractions disappear.

Example

```
commerce.order.read
```

↓

Capability Graph

↓

```
shopify.get_order
```

or

```
woocommerce.get_order
```

depending on tenant configuration.

The planner never knows.

---

# Phase 3 — Policy Expansion

Planner says

```
Approval Required
```

Compiler inserts

```
human.approval
```

runtime node.

Planner stays simple.

Compiler expands execution.

---

# Example

Workflow IR

```
Refund

↓

Reply
```

Compiler

↓

```
Refund

↓

Approval

↓

Reply
```

if policy requires approval.

---

# Phase 4 — Runtime Expansion

One business step may become many runtime nodes.

Example

Business

```
Generate Reply
```

Compiler

↓

```
Knowledge Search

↓

Agent

↓

Response
```

Business layer remains clean.

---

# Phase 5 — Runtime Metadata

Compiler fills runtime metadata.

Example

```
retry

timeout

checkpoint

cost

node ids

internal names
```

Planner never creates these.

---

# Runtime IDs

Compiler generates stable ids.

Example

```
reply

↓

reply_001
```

or

```
reply_agent
```

IDs become deterministic.

This improves:

Replay

Snapshots

Persistence

Diff

Resume

---

# Runtime Variables

Compiler assigns variable names.

Example

```
Read Order

↓

order
```

↓

```
vars.order
```

↓

Next node consumes

```
vars.order
```

No planner involvement.

---

# Provider Selection

Capability

```
commerce.order.read
```

may compile differently.

Shopify

↓

```
shopify.get_order
```

WooCommerce

↓

```
woocommerce.get_order
```

Stripe

↓

```
stripe.invoice.read
```

Planner remains identical.

---

# Parallelization

Compiler detects independent work.

Workflow IR

```
Read Order

Read Customer

Search KB
```

Compiler

↓

Parallel runtime branches.

Current runtime already supports parallel execution.

Compiler simply uses it.

---

# Automatic Join

Compiler inserts joins automatically.

Planner

```
A

B

↓

Reply
```

Compiler

↓

```
A

||

B

↓

join.all

↓

Reply
```

Planner never creates join nodes.

---

# Approval Expansion

Workflow IR

```
Refund
```

Compiler

↓

```
Refund Policy

↓

Approval

↓

Refund

↓

Reply
```

---

# Verification Expansion

Planner

```
Generate Reply
```

Compiler

↓

```
Generate Reply

↓

Verify Reply

↓

Return
```

Verification becomes automatic.

---

# Repair Expansion

Planner

```
Generate Reply
```

Compiler

↓

```
Generate Reply

↓

Verify

↓

Repair

↓

Verify Again

↓

Return
```

No planner complexity.

---

# Runtime Optimization

Compiler removes unnecessary work.

Example

Duplicate KB searches

↓

Single shared node

Duplicate customer lookup

↓

Single lookup

Dead branches

↓

Removed

Unused outputs

↓

Removed

---

# Compiler Validation

Before returning workflow

Compiler checks

Every node reachable

Every dependency satisfied

No cycles

Known node types

Known configs

Valid runtime schema

Every edge valid

---

# Compiler Output Contract

Always returns

```json
{
    "workflow":{},
    "metadata":{},
    "warnings":[]
}
```

Warnings may include

High cost

Missing optional verification

Long latency

Large context

---

# Current Tajeran Mapping

Already Exists

✅ Runtime Executor

✅ Runtime Nodes

✅ Registry

✅ Parallel Execution

✅ Join Node

✅ Approval Node

✅ Persistence

✅ Replay

✅ Resume

Missing

❌ Workflow Compiler

❌ Capability Resolver

❌ Policy Expander

❌ Runtime Optimizer

---

# Suggested Backend Structure

```
app/planner/compiler/

    compiler.py

    capability_resolver.py

    policy_expander.py

    optimizer.py

    runtime_builder.py

    validator.py
```

---

# Compiler API

```python
workflow = compiler.compile(
    workflow_ir,
    tenant_context,
)
```

Returns

```
Runtime DAG
```

ready for execution.

---

# Testing Strategy

Compiler tests are deterministic.

Input

↓

Expected Runtime DAG

Every compiler feature should have golden-file tests.

Example

```
refund.json

↓

refund_runtime.json
```

Compiler output must match exactly.

---

# MVP

Version 1 compiler only needs to support

Capability resolution

Sequential workflows

Existing runtime nodes

Approval insertion

Response node insertion

No optimization yet.

---

# Long-Term Vision

Eventually

```
User Prompt

↓

Planner

↓

Workflow IR

↓

Compiler

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

The runtime never knows prompts.

The planner never knows runtime nodes.

The compiler is the only translator.

This separation is what allows Tajeran to evolve each layer independently.

---

# Current Readiness

Runtime Engine

★★★★★

Workflow Nodes

★★★★★

Planner

★☆☆☆☆

Workflow IR

★☆☆☆☆

Workflow Compiler

☆☆☆☆☆

---

# Next Investigation

**Stage 14 — Capability Resolver**

This is one of the most important components in the entire architecture.

It transforms abstract business capabilities such as:

```
commerce.order.read
```

into concrete runtime implementations like:

```
shopify.get_order
```

or

```
woocommerce.get_order
```

without the planner ever knowing which provider is being used.