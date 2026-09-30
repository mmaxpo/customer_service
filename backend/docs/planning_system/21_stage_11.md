# Stage 11 — Planning Graph

Version: 0.1

---

# Purpose

The Planning Graph is the planner’s central reasoning structure.

It sits between:

```
Business Object Graph

↓

Capability Graph

↓

Runtime Workflow
```

The planner should never jump directly from prompt to runtime JSON.

It should first create a Planning Graph.

---

# Core Idea

A Planning Graph represents:

```
Goal

Objects

Capabilities

Dependencies

Constraints

Risks

Approvals

Expected Outputs
```

It is the planner’s map before execution.

---

# Why It Exists

Without Planning Graph:

```
Prompt

↓

Runtime Nodes
```

This is fragile.

With Planning Graph:

```
Prompt

↓

Intent

↓

Objects

↓

Capabilities

↓

Planning Graph

↓

Validated Runtime Workflow
```

This is explainable and production-grade.

---

# Planning Graph Definition

A Planning Graph contains planning nodes.

Each planning node represents a business task.

Example:

```json
{
  "id": "read_order",
  "type": "business_task",
  "goal": "Read the customer order",
  "capability_id": "commerce.order.read",
  "inputs": ["order_ref"],
  "outputs": ["order"],
  "risk": "low"
}
```

---

# Planning Node Types

## Task Node

Represents work to be done.

Example:

```
Read Order
```

---

## Decision Node

Represents branching.

Example:

```
Is refund eligible?
```

---

## Approval Node

Represents human gate.

Example:

```
Manager approves refund
```

---

## Verification Node

Represents quality check.

Example:

```
Verify reply follows policy
```

---

## Repair Node

Represents recovery.

Example:

```
Retry knowledge search
```

---

## Result Node

Represents final output.

Example:

```
Customer-facing reply
```

---

# Planning Graph Example

Prompt:

```
Customer says item arrived damaged and wants refund.
```

Planning Graph:

```
Understand Conversation

↓

Read Order

↓

Search Refund Policy

↓

Evaluate Refund Eligibility

↓

Human Approval

↓

Create Refund

↓

Generate Reply

↓

Verify Reply

↓

Return Result
```

---

# Graph Edges

Edges represent dependency.

Example:

```
Create Refund
```

depends on:

```
Read Order

Approval

Refund Eligibility
```

Edges are not UI lines.

They are business requirements.

---

# Edge Types

## Data Dependency

```
Read Order

↓

Refund Decision
```

because refund decision needs order data.

---

## Control Dependency

```
Approval

↓

Refund
```

because refund cannot happen before approval.

---

## Policy Dependency

```
Search Policy

↓

Decision
```

because decision must use policy.

---

## Verification Dependency

```
Generate Reply

↓

Verify Reply
```

because output must be checked.

---

# Planning Graph Fields

```json
{
  "goal": "...",
  "objects": [],
  "nodes": [],
  "edges": [],
  "constraints": [],
  "risks": [],
  "expected_outputs": [],
  "verification_policy": "...",
  "repair_policy": "..."
}
```

---

# Difference From Runtime DAG

Runtime DAG:

```
trigger.message

agent.custom

shopify.get_order

response
```

Planning Graph:

```
Understand request

Read order

Decide refund

Ask approval

Notify customer
```

Runtime is implementation.

Planning Graph is business reasoning.

---

# Why This Matters

The Planning Graph allows Tajeran to:

- explain the plan
- validate before execution
- estimate cost
- identify risk
- insert approval
- optimize parallel work
- repair failures
- compile to different runtimes later

---

# Validation

Before compiling, planner validates:

```
Are all inputs known?

Are all outputs produced?

Are high-risk actions approved?

Are dependencies valid?

Are there cycles?

Are there impossible steps?

Are required capabilities available?
```

Invalid graph never reaches runtime.

---

# Optimization

Planner can optimize graph.

Example:

```
Read Order

Search Policy

Analyze Sentiment
```

can run in parallel.

The Planning Graph makes this visible before compilation.

---

# Repair

If verification fails, repair modifies the Planning Graph.

Example:

Original:

```
Generate Reply
```

Repair inserts:

```
Search Policy

↓

Generate Improved Reply

↓

Verify Again
```

---

# Current Tajeran Mapping

Already exists:

```
Runtime DAG

Node execution

Edges

Events

State

Timeline

Snapshots
```

Missing:

```
Planning Graph model

Planning graph validator

Planning graph compiler

Planning graph optimizer

Planning graph repair
```

---

# Suggested Backend Location

```text
app/planner/graph/
    schemas.py
    builder.py
    validator.py
    optimizer.py
    compiler.py
    repair.py
```

---

# Minimal First Version

First Planning Graph should support only:

```
Task Node

Approval Node

Result Node

Data Dependency

Control Dependency
```

Do not start too large.

---

# First Vertical Slice

Prompt:

```
Create a workflow for damaged item refund replies.
```

Planning Graph:

```
Trigger Message

↓

Generate Reply

↓

Return Response
```

Then expand to:

```
Trigger Message

↓

Read Order

↓

Generate Reply

↓

Return Response
```

Then:

```
Trigger Message

↓

Read Order

↓

Approval

↓

Generate Reply

↓

Return Response
```

---

# Current Readiness

Runtime DAG

★★★★★

Runtime Validation

★★★★☆

Business Planning Graph

☆☆☆☆☆

Planning Graph Compiler

☆☆☆☆☆

Planning Graph Repair

☆☆☆☆☆

---

# Next Investigation

Stage 12 — Workflow IR

The Planning Graph is still business-level.

The Workflow IR is the bridge between planning and runtime.

It converts:

```
Business Plan
```

into:

```
Executable workflow structure
```

but still stays cleaner and more stable than raw React Flow or runtime JSON.