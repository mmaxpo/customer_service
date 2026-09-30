# Stage 15 — Workflow Generator

Version: 0.1

---

# Purpose

The Workflow Generator is the first component that makes Tajeran truly intelligent.

Everything before this stage prepared knowledge.

This stage creates solutions.

Its job is simple:

```
Given a business goal,

generate the best executable workflow.
```

---

# Philosophy

Current workflow systems work like this:

```
Human

↓

Drag Nodes

↓

Workflow
```

Tajeran should work like this:

```
Human Goal

↓

Planner

↓

Workflow Generator

↓

Workflow

↓

Execution
```

The workflow becomes an AI-generated artifact.

---

# The Biggest Mindset Shift

Today your runtime executes workflows.

Tomorrow your platform creates workflows.

Execution becomes a solved problem.

Planning becomes the product.

---

# Generator Responsibilities

Workflow Generator is responsible for:

- understanding the business goal
- selecting business capabilities
- building execution order
- choosing agents
- deciding parallel work
- inserting approvals
- inserting verification
- inserting repair
- producing Workflow IR

It is NOT responsible for:

- executing
- compiling
- calling runtime nodes
- provider selection

---

# Input

Planner provides

```json
{
  "goal":"Handle damaged order refund request",

  "intent":"refund",

  "objects":[
      "customer",
      "order"
  ],

  "constraints":[
      "company_policy"
  ]
}
```

---

# Output

Workflow IR

Example

```
Trigger

↓

Read Order

↓

Search Policy

↓

Evaluate Eligibility

↓

Approval

↓

Issue Refund

↓

Generate Reply

↓

Verify

↓

Return
```

---

# Workflow Generation Pipeline

```
Prompt

↓

Intent

↓

Business Objects

↓

Capabilities

↓

Planning Graph

↓

Workflow Generator

↓

Workflow IR
```

---

# Generator Does NOT Generate Nodes

Important.

It generates business tasks.

Not runtime nodes.

Bad

```
shopify.get_order
```

Good

```
Read Order
```

The compiler handles implementation.

---

# Generator Uses Templates

Generation is not random.

It combines

Templates

+

Planning

+

Reasoning

+

Business Rules

---

# Example

Prompt

```
Refund damaged item
```

Generator starts with

```
Refund Template
```

Then adapts it.

---

# Templates Are Skeletons

Example

Refund Skeleton

```
Read Order

↓

Evaluate Refund

↓

Approval

↓

Refund

↓

Reply
```

Generator fills details.

---

# Generator Uses Capability Graph

Instead of inventing actions

it asks

```
What capabilities exist?
```

Example

```
Refund

↓

Read Order

↓

Read Customer

↓

Knowledge Search

↓

Refund

↓

Generate Reply
```

Every step comes from capability discovery.

---

# Generator Uses Planning Graph

Planning Graph already contains

Goals

Dependencies

Constraints

Risks

Expected outputs

Workflow Generator converts these into execution.

---

# Generator Can Create Parallel Work

Instead of

```
Read Order

↓

Read Customer

↓

Search KB
```

Generator creates

```
Read Order

||

Read Customer

||

Search KB
```

Planner becomes much faster.

---

# Generator Inserts Approvals

Planner identifies

```
High Risk
```

Generator inserts

```
Approval
```

No human workflow design.

---

# Generator Inserts Verification

Every customer-facing output becomes

```
Reply

↓

Verify
```

No manual configuration required.

---

# Generator Inserts Repair

Generator automatically creates

```
Reply

↓

Verify

↓

Repair

↓

Verify Again
```

instead of ending on failure.

---

# Workflow Generation Strategy

The generator should never rely on one LLM call.

Instead

```
Generate Draft

↓

Validate

↓

Improve

↓

Verify

↓

Finalize
```

The workflow itself is generated iteratively.

---

# Generation Constraints

Workflow Generator always respects

Maximum cost

Maximum latency

Maximum depth

Available capabilities

Installed providers

Human approval policy

Business rules

Compliance

---

# Deterministic Generation

The same prompt should produce nearly identical workflows.

Random creativity is undesirable.

Generation should be guided by

Templates

Capabilities

Business ontology

Planner memory

Policies

---

# Explainability

Every generated workflow should include

Why each step exists.

Example

```
Read Order

Reason:

Needed to verify eligibility.
```

This allows humans to review plans.

---

# Workflow Confidence

Generator returns

```json
{
    "confidence":0.93
}
```

Low confidence workflows may require review.

---

# Alternative Plans

Instead of generating only one workflow

Generator may produce

```
Plan A

Plan B

Plan C
```

Planner chooses.

Example

Fast

↓

Cheap

↓

Highest Quality

---

# Planning Metadata

Generated workflow includes

Estimated latency

Estimated token cost

Risk level

Complexity

Approval count

Verification count

Expected tools

---

# Self Review

Generator reviews itself.

```
Workflow

↓

Critic

↓

Improve

↓

Final
```

Before runtime.

---

# Human Editable

Generated workflow is not locked.

User may edit

Approve

Delete

Add

Replace

before execution.

This is where your future frontend becomes incredibly powerful.

---

# Current Tajeran Mapping

Already Exists

✅ Runtime DAG

✅ Node Registry

✅ Agent Nodes

✅ Parallel Execution

✅ Approval Nodes

✅ Verification Support

✅ Response Nodes

Missing

❌ Workflow Generator

❌ Workflow Skeleton Library

❌ Planning Templates

❌ Generator Critic

❌ Alternative Workflow Search

---

# Suggested Backend Structure

```
app/planner/generator/

    generator.py

    templates.py

    skeletons.py

    planner.py

    reviewer.py

    validator.py
```

---

# Skeleton Library

Eventually Tajeran should ship with hundreds of workflow skeletons.

Examples

```
Customer Support

Refund

Replacement

Order Tracking

Returns

Lead Qualification

Sales

Marketing

HR

IT Helpdesk

Legal

Finance

Healthcare
```

Each becomes a reusable planning primitive.

---

# Why This Is Different

Today's no-code builders ask

> "What nodes do you want?"

Tajeran asks

> "What business outcome do you want?"

That difference changes everything.

---

# MVP

Version 1 only needs

- One Workflow Generator
- Small skeleton library
- Capability selection
- Sequential workflows
- Workflow IR generation

No optimization yet.

---

# Long-Term Vision

```
User Prompt

↓

Intent Extraction

↓

Planning Graph

↓

Workflow Generator

↓

Workflow IR

↓

Compiler

↓

Runtime DAG

↓

Execution
```

At this point Tajeran stops being a workflow editor.

It becomes an AI system that designs workflows on behalf of the user.

---

# Current Readiness

Execution Runtime

★★★★★

Planning System

★★☆☆☆

Workflow Generator

☆☆☆☆☆

Template Library

☆☆☆☆☆

Planning Intelligence

☆☆☆☆☆

---

# Next Investigation

## Stage 16 — Planner LLM

This is arguably the most important AI component in Tajeran.

Rather than being "the AI that answers users," it becomes **the AI architect** that reasons about business problems, generates execution plans, critiques them, and coordinates every other intelligence component in the platform.