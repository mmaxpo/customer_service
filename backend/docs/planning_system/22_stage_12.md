# Stage 12 — Workflow IR (Intermediate Representation)

Version: 0.1

---

# Purpose

The Workflow IR is the bridge between planning and execution.

It converts:

```
Planning Graph
```

into

```
Executable Runtime Workflow
```

without exposing runtime implementation details.

Think of it as the compiler's internal language.

```
Prompt

↓

Intent

↓

Planning Graph

↓

Workflow IR

↓

Runtime DAG

↓

Execution
```

---

# Why Workflow IR Exists

Without an intermediate layer:

```
Planner

↓

ReactFlow JSON
```

The planner becomes tightly coupled to:

- UI
- runtime engine
- node schema
- execution implementation

Every runtime change breaks planning.

Workflow IR removes this coupling.

---

# Compiler Analogy

Programming language:

```
C

↓

LLVM IR

↓

Machine Code
```

Tajeran:

```
Business Plan

↓

Workflow IR

↓

Runtime Workflow
```

The runtime never receives business concepts.

The runtime receives executable instructions.

---

# Responsibilities

Workflow IR is responsible for:

- execution order
- dependencies
- runtime metadata
- retry strategy
- timeout
- approval policy
- verification
- repair
- routing

NOT for:

- ReactFlow coordinates
- UI colors
- frontend metadata
- drag/drop state

---

# Workflow IR Structure

```json
{
  "workflow_id": "...",

  "steps": [],

  "links": [],

  "metadata": {},

  "policies": {},

  "verification": {},

  "repair": {}
}
```

---

# Workflow Step

Example

```json
{
  "id":"read_order",

  "type":"capability",

  "capability":"commerce.order.read",

  "inputs":[
      "order_ref"
  ],

  "outputs":[
      "order"
  ]
}
```

Notice

No ReactFlow.

No runtime node.

Only execution semantics.

---

# Step Types

## Capability

Calls capability graph.

Example

```
knowledge.search

commerce.order.read

refund.create
```

---

## Decision

Represents planner decision.

Example

```
Refund Eligible?
```

---

## Approval

Represents human approval.

```
Manager Approval
```

---

## Verification

Represents quality evaluation.

```
Policy Verification
```

---

## Repair

Represents automatic recovery.

```
Retry Search
```

---

## Result

Represents final output.

```
Customer Reply
```

---

# Step Example

```json
{
  "id":"verify",

  "type":"verification",

  "policy":"reply_quality",

  "retry":true,

  "max_retry":2
}
```

---

# Links

Workflow IR edges represent execution dependency.

```json
{
  "from":"read_order",

  "to":"refund_decision"
}
```

Unlike runtime edges they contain semantics.

---

# Metadata

Workflow metadata is execution independent.

Example

```json
{
  "priority":"normal",

  "estimated_cost":420,

  "estimated_latency":3.4,

  "risk":"medium"
}
```

Planner creates this.

Runtime consumes it.

---

# Policies

Policies travel with the workflow.

Example

```json
{
    "approval_required":true,

    "timeout":120,

    "retry_limit":2
}
```

Planner determines these.

Runtime enforces them.

---

# Verification

Verification is part of Workflow IR.

Example

```json
{
    "policy":"customer_reply",

    "judge":"llm",

    "minimum_score":0.85
}
```

---

# Repair

Workflow IR contains repair strategy.

Example

```json
{
    "strategy":"retry",

    "max_attempts":2,

    "fallback":"human"
}
```

---

# Compilation

Workflow IR compiles into Runtime DAG.

Example

Planning Graph

```
Read Order

↓

Create Reply
```

Workflow IR

```
Step 1

Capability

↓

Step 2

Capability
```

Runtime DAG

```
shopify.get_order

↓

agent.custom

↓

response
```

Notice

Runtime node names only appear at compilation.

---

# Runtime Mapping

Compiler maps:

```
commerce.order.read
```

↓

```
shopify.get_order
```

or

↓

```
woocommerce.get_order
```

depending on tenant.

Business workflow never changes.

---

# Multi-runtime Future

Workflow IR enables multiple execution engines.

Today

```
Runtime DAG
```

Future

```
Runtime DAG

LangGraph

Temporal

Ray

Distributed Cluster

Cloud Execution
```

Planner remains identical.

---

# Optimization

Workflow IR optimizer may:

Merge steps

Remove duplicates

Parallelize

Insert cache

Insert checkpoint

Insert approval

Insert retries

before runtime generation.

---

# Example

Workflow IR

```
Read Order

↓

Read Customer

↓

Search Knowledge
```

Optimizer

↓

```
Read Order

||

Read Customer

||

Search Knowledge
```

Runtime receives parallel graph.

---

# Versioning

Workflow IR should be versioned.

```json
{
    "ir_version":"1.0"
}
```

Future compiler versions remain backward compatible.

---

# Validation

Workflow IR validator checks

Missing inputs

Circular dependencies

Unknown capability

Invalid policies

Approval loops

Duplicate outputs

Timeout conflicts

Impossible execution

before runtime generation.

---

# Current Tajeran Mapping

Already Exists

✅ Runtime DAG

✅ Node Registry

✅ Runtime Executor

✅ State Engine

✅ Event Store

✅ Persistence

Missing

❌ Workflow IR Schema

❌ Workflow Compiler

❌ Workflow Validator

❌ Workflow Optimizer

❌ Runtime Translator

---

# Suggested Backend Structure

```
app/planner/workflow_ir/

    schemas.py

    compiler.py

    validator.py

    optimizer.py

    translator.py
```

---

# Translator Responsibility

Translator converts

```
Workflow IR
```

↓

```
Runtime DAG
```

using the Capability Graph.

Example

```
commerce.order.read
```

↓

```
shopify.get_order
```

without planner knowing anything about Shopify.

---

# Why This Layer Matters

Without Workflow IR

```
Planner

↓

Runtime JSON
```

Every runtime change requires planner updates.

With Workflow IR

```
Planner

↓

Workflow IR

↓

Runtime Compiler

↓

Runtime DAG
```

Planner remains stable.

Runtime can evolve independently.

---

# MVP

Version 1 should support only

Capability Step

Decision Step

Approval Step

Verification Step

Result Step

Sequential dependencies

Compilation to existing Runtime DAG

Nothing more.

---

# Long-Term Vision

Eventually the complete pipeline becomes

```
User Prompt

↓

Intent Extraction

↓

Business Objects

↓

Capability Selection

↓

Planning Graph

↓

Workflow IR

↓

Runtime Compiler

↓

Workflow DAG

↓

Execution Engine

↓

Verification

↓

Repair

↓

Result
```

---

# Current Readiness

Execution Runtime

★★★★★

Planning Graph

★☆☆☆☆

Workflow IR

☆☆☆☆☆

Compiler

☆☆☆☆☆

Planner

☆☆☆☆☆

---

# Next Investigation

Stage 13 — Workflow Compiler

The Workflow IR is still abstract.

The Workflow Compiler is the component that transforms Workflow IR into the exact Runtime DAG already supported by Tajeran's execution engine.