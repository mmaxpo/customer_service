# Stage 08 — Planner Internal Architecture

Version: 0.1

---

# Purpose

The Planner is not a class.

The Planner is not one LLM prompt.

The Planner is an internal operating system composed of specialized reasoning services.

Every service owns exactly one responsibility.

Execution Runtime executes.

Planner Runtime thinks.

---

# High Level Architecture

```
                    User Prompt

                         │

                         ▼

                Planning Runtime

────────────────────────────────────────────

Intent Engine

↓

Business Understanding Engine

↓

Business Object Builder

↓

Constraint Engine

↓

Capability Resolver

↓

Dependency Planner

↓

Task Graph Builder

↓

Workflow Compiler

↓

Validator

↓

Optimizer

↓

Execution Coordinator

↓

Verification Engine

↓

Repair Planner

↓

Learning Engine

────────────────────────────────────────────

Workflow Runtime

↓

Execution Runtime

↓

Events

↓

Persistence
```

Notice

Execution Runtime is unchanged.

Planner Runtime sits entirely above it.

---

# Planner Runtime

Planner Runtime becomes a new subsystem.

```
app/planner/
```

not

```
runtime/
```

because it does not execute.

It reasons.

---

Suggested structure

```
planner/

    intent/

    business/

    capabilities/

    graph/

    compiler/

    validator/

    optimizer/

    verifier/

    repair/

    learning/

    memory/

    models/

    services/

    prompts/
```

Exactly like Runtime today.

Small services.

Single responsibility.

---

# 1 Intent Engine

Purpose

Convert natural language into structured intent.

Input

```
Refund my damaged order.
```

Output

```
Primary Goal

Refund

Confidence

Objects Mentioned

Possible Domains

Unknown Information
```

Never builds workflow.

Only understands.

---

Responsibility

```
Prompt

↓

Intent Model
```

Nothing else.

---

# 2 Business Understanding Engine

Purpose

Understand business semantics.

Example

Prompt

```
Customer wants replacement.
```

Engine discovers

```
Customer

Conversation

Order

Inventory

Replacement

Policy
```

Produces

Business Context.

---

# 3 Business Object Builder

Purpose

Create structured object graph.

Output

```
Customer

↓

Conversation

↓

Order

↓

Shipment
```

Planner now reasons using objects.

---

# 4 Constraint Engine

Purpose

Discover restrictions.

Examples

```
Approval

Policy

Permission

Business Hours

Compliance

Security

SLA

Token Budget
```

Outputs

Constraint Model.

---

# 5 Capability Resolver

Purpose

Search Capability Registry.

Input

```
Need refund.
```

Output

```
Read Order

↓

Eligibility

↓

Refund

↓

Reply
```

No workflow generation.

Only capability discovery.

---

# 6 Dependency Planner

Purpose

Order capabilities.

Input

```
Capabilities
```

Output

```
Graph
```

Example

```
Read Order

↓

Refund

↓

Reply
```

No runtime nodes yet.

---

# 7 Task Graph Builder

Purpose

Convert dependency graph into business graph.

Example

```
Goal

↓

Tasks

↓

Subtasks

↓

Parallel Tasks

↓

Human Approval
```

Planner graph complete.

Still runtime independent.

---

# 8 Workflow Compiler

Purpose

Translate business graph into Runtime DAG.

Example

Business Graph

↓

Runtime Nodes

↓

Edges

↓

Node Config

↓

Variables

↓

Workflow JSON

Exactly what your Runtime already executes.

---

# 9 Validator

Purpose

Reject bad workflows.

Checks

```
Cycles

Missing Inputs

Missing Approval

Unknown Capability

Permission

Impossible Path

Dead Nodes

Invalid Outputs
```

Produces

Validation Report.

---

# 10 Optimizer

Purpose

Improve workflow.

Example

Planner generated

```
Knowledge Search

↓

Knowledge Search

↓

Knowledge Search
```

Optimizer

↓

Merge

Planner generated

```
Sequential

```

Optimizer

↓

Parallel

Planner generated

```
GPT-5

```

Optimizer

↓

GPT-5 Nano

when acceptable.

---

# 11 Execution Coordinator

Purpose

Bridge Planner Runtime

↓

Execution Runtime

Responsibilities

```
Submit Workflow

Monitor Events

Collect Results

Update Memory

Handle Interrupts
```

It never executes nodes.

Runtime owns execution.

---

# 12 Verification Engine

Purpose

Verify business success.

Example

Refund workflow.

Checks

```
Refund Created

Conversation Updated

Customer Notified
```

Execution success

≠

Business success.

---

# 13 Repair Planner

Purpose

Generate repair graph.

Example

Knowledge Search failed.

↓

Retry

or

Fallback

or

Human

Produces

Repair Workflow.

---

# 14 Learning Engine

Purpose

Observe every execution.

Stores

```
Success Rate

Cost

Duration

Planner Decisions

Common Graphs

Failure Patterns

Optimization Opportunities
```

Eventually planner improves itself.

---

# Planner Memory

Shared by every planner service.

Contains

```
Working Memory

Capability Memory

Decision Memory

Execution Memory

Experience Memory
```

Already defined.

---

# Planner Models

Planner services exchange models.

Never raw JSON.

Examples

```
IntentModel

BusinessModel

ConstraintModel

CapabilityGraph

TaskGraph

WorkflowPlan

ValidationReport

OptimizationReport

VerificationReport
```

Everything becomes typed.

---

# Planner Flow

```
Prompt

↓

Intent Engine

↓

Business Engine

↓

Object Builder

↓

Constraint Engine

↓

Capability Resolver

↓

Dependency Planner

↓

Task Graph

↓

Workflow Compiler

↓

Validator

↓

Optimizer

↓

Execution Coordinator

↓

Runtime

↓

Verification

↓

Repair

↓

Learning
```

Every service has one responsibility.

---

# Why So Many Services?

Because planners evolve.

Tomorrow

you may replace

Intent Engine

without touching

Workflow Compiler.

Or replace

Validator

without touching

Repair Planner.

Exactly the philosophy used in Runtime today.

---

# Planner vs Runtime

Planner answers

```
What should happen?
```

Runtime answers

```
How does it happen?
```

This separation keeps both systems simple.

---

# Mapping to Existing Backend

Already Exists

Execution Runtime

★★★★★

Workflow Runtime

★★★★★

Agent Runtime

★★★★★

Node Catalog

★★★★★

Persistence

★★★★★

Replay

★★★★★

Event System

★★★★★

Planner Runtime

☆☆☆☆☆

The Planner Runtime becomes a new top-level subsystem that leverages—not replaces—the existing execution infrastructure.

---

# Why This Architecture Is Different

Most agent frameworks have a single reasoning loop.

Tajeran has specialized reasoning engines collaborating to build an execution plan.

That makes the system:

- easier to test
- easier to extend
- easier to optimize
- easier to explain
- more deterministic
- more production-ready

---

# Long-Term Vision

Eventually the Planner Runtime becomes reusable across every product.

Customer Service

↓

HR

↓

CRM

↓

Finance

↓

Marketing

↓

Sales

↓

Operations

↓

Software Engineering

The Runtime stays the same.

Only capabilities and business objects change.

Planner intelligence becomes a platform capability.

---

# Current Readiness

Execution Runtime        ★★★★★

Workflow Runtime         ★★★★★

Agent Runtime            ★★★★★

Planner Runtime          ☆☆☆☆☆

Internal Planner Services ☆☆☆☆☆

This document defines the production architecture for the next major subsystem of Tajeran.

---

# Next Investigation

Stage 09 — Capability Registry

The planner cannot discover capabilities until there is a production-grade registry describing every capability in the platform.

This registry becomes the "knowledge base of everything Tajeran can do."

It will eventually contain thousands of capabilities across all future products.