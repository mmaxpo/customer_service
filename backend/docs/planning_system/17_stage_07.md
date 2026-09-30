# Stage 07 — Planner Reasoning Pipeline

Version: 0.1

---

# Purpose

The Planner is not a single LLM prompt.

It is a deterministic reasoning pipeline.

Every request follows the same cognitive process.

Instead of

```
Prompt

↓

LLM

↓

Answer
```

Tajeran becomes

```
Prompt

↓

Understand

↓

Model

↓

Plan

↓

Validate

↓

Optimize

↓

Execute

↓

Verify

↓

Repair

↓

Result
```

The LLM participates in several stages.

It does **not** control the architecture.

---

# Core Principle

Planning is a sequence of reasoning phases.

Every phase has

- inputs
- outputs
- validations

Each phase improves certainty before execution begins.

---

# Complete Pipeline

```
User Prompt

↓

Intent Extraction

↓

Business Understanding

↓

Object Discovery

↓

Constraint Discovery

↓

Capability Discovery

↓

Graph Planning

↓

Dependency Resolution

↓

Risk Analysis

↓

Cost Optimization

↓

Workflow Generation

↓

Workflow Validation

↓

Execution

↓

Monitoring

↓

Verification

↓

Repair

↓

Learning

↓

Result
```

---

# Stage 1

Intent Extraction

Purpose

Understand

"What does the user actually want?"

Example

```
Refund my damaged order.
```

Planner extracts

```
Primary Goal

Refund

Secondary

Damaged Product

Confidence

97%
```

Output

```
Intent Model
```

---

# Stage 2

Business Understanding

Purpose

Translate natural language into business meaning.

Planner discovers

```
Customer

Conversation

Order

Refund

Policy
```

instead of

```
Prompt
```

Output

```
Business Model
```

---

# Stage 3

Business Object Discovery

Planner identifies objects.

Example

```
Customer

Order

Conversation

Knowledge

Approval
```

Missing objects become tasks.

Example

Need Order.

↓

Read Order.

---

# Stage 4

Constraint Discovery

Planner discovers rules.

Examples

```
Refund Policy

Manager Approval

Available Inventory

Business Hours

Permissions

Security

SLA
```

Without constraints

planning is unsafe.

---

# Stage 5

Capability Discovery

Planner asks

```
What capabilities solve this goal?
```

Example

```
Read Order

↓

Refund

↓

Generate Reply
```

Planner searches Capability Registry.

Output

Capability Set.

---

# Stage 6

Dependency Resolution

Planner orders work.

Instead of

```
Refund

Read Order
```

Planner builds

```
Read Order

↓

Refund
```

Dependency graph created.

---

# Stage 7

Parallel Opportunity Detection

Planner asks

```
What can execute simultaneously?
```

Example

```
Read Order

Knowledge Search

Sentiment Analysis

Policy Search
```

run together.

Planner reduces latency.

---

# Stage 8

Risk Analysis

Planner evaluates

```
Financial Risk

Security

Compliance

Customer Impact

Confidence

Permissions
```

Example

Refund

↓

High Risk

↓

Approval Required

Planner inserts approval automatically.

---

# Stage 9

Cost Optimization

Planner estimates

```
Token Usage

API Calls

Latency

Money

Complexity
```

Example

Knowledge already cached.

↓

Skip search.

Planner minimizes cost.

---

# Stage 10

Workflow Generation

Planner finally builds

Business Graph

↓

Workflow Graph

↓

Runtime DAG

Planner still has not executed anything.

---

# Stage 11

Workflow Validation

Planner checks

```
Missing Inputs

Cycles

Unknown Capabilities

Permissions

Impossible Steps

Approval

Tool Availability
```

Invalid graph

↓

Repair.

---

# Stage 12

Execution

Only now

Planner hands graph to Runtime.

Runtime

↓

Execution Engine

↓

Nodes

↓

Events

↓

Persistence

Planner observes.

Runtime executes.

---

# Stage 13

Monitoring

Planner watches execution.

```
Completed

Waiting

Failed

Retry

Approval

Latency

Usage
```

Planner continuously updates Working Memory.

---

# Stage 14

Verification

Execution succeeded.

Planner asks

```
Was the goal actually achieved?
```

Example

Refund created.

↓

Customer notified.

↓

Conversation updated.

↓

Done.

---

# Stage 15

Repair

If verification fails

Planner builds a repair graph.

Example

```
Knowledge Missing

↓

Search Again

↓

Generate New Reply
```

No human required.

---

# Stage 16

Learning

Planner records

```
Intent

Workflow

Duration

Failures

Success

Capabilities Used

Cost

Confidence
```

Experience Memory updated.

Future planning improves.

---

# Visual Pipeline

```
Prompt

↓

Intent

↓

Business Understanding

↓

Objects

↓

Capabilities

↓

Dependencies

↓

Graph

↓

Validation

↓

Optimization

↓

Execution

↓

Monitoring

↓

Verification

↓

Repair

↓

Learning

↓

Result
```

Every phase has one responsibility.

---

# Deterministic vs Generative

Some phases are deterministic.

Examples

```
Dependency Resolution

Validation

Optimization

Execution
```

Some phases use LLM reasoning.

Examples

```
Intent

Business Understanding

Capability Selection

Repair Strategy
```

Planner combines both.

---

# Human Approval

Approval is just another phase.

Planner inserts

```
Approval

↓

Resume
```

without changing architecture.

Already supported by your runtime.

---

# Runtime Relationship

Planner

↓

Workflow Graph

↓

Runtime DAG

↓

Execution Runtime

↓

Events

↓

Verification

Planner never executes nodes directly.

Runtime owns execution.

---

# Memory Usage

Each phase updates memory.

Intent

↓

Working Memory

Capabilities

↓

Capability Memory

Execution

↓

Execution Memory

Verification

↓

Verification Memory

Learning

↓

Experience Memory

Planner never loses context.

---

# Failure Recovery

Failure

↓

Understand Failure

↓

Locate Broken Capability

↓

Generate Repair Graph

↓

Validate

↓

Execute Repair

↓

Verify Again

Planner recovers automatically.

---

# Future Recursive Planning

Large goals become smaller goals.

Example

```
Launch my Shopify support system.
```

Planner decomposes

```
Connect Shopify

↓

Configure Inbox

↓

Create Workflows

↓

Import Knowledge

↓

Configure Agents

↓

Verification
```

Every subgoal follows the same pipeline.

Recursive planning emerges naturally.

---

# Current Backend Mapping

Already Exists

★★★★★

Execution Runtime

★★★★★

Workflow Runtime

★★★★★

Agent Runtime

★★★★★

Events

★★★★★

Persistence

★★★★★

Replay

★★★★★

Human Approval

★★★★☆

Verification

★★★☆☆

Planner Pipeline

☆☆☆☆☆

This pipeline is the missing orchestration layer.

---

# Future Pipeline

Prompt

↓

Planner

↓

Business Graph

↓

Workflow Graph

↓

Execution Runtime

↓

Monitoring

↓

Repair

↓

Learning

↓

Experience

↓

Better Planner

Every execution improves future planning.

---

# Why This Stage Matters

This is the architectural boundary between

an execution engine

and

an intelligent operating system.

Your runtime already knows **how to execute**.

This planner will know **what should be executed, why, in what order, at what cost, under which constraints, and how to recover if reality changes.**

That is a fundamentally different capability.

---

# Current Readiness

Execution Runtime

95%

Agent Runtime

90%

Business Objects

20%

Capability Ontology

15%

Planner Memory

10%

Planner Pipeline

0%

Workflow Generation

10%

Learning System

0%

After implementing this pipeline, the remaining work is mostly adding intelligence into each phase rather than redesigning the architecture.

---

# Next Investigation

Stage 08

Planner Internal Architecture

The next document defines the actual internal services that implement this pipeline.

Instead of one "Planner" class, Tajeran will have specialized components such as:

- Intent Engine
- Business Model Builder
- Capability Resolver
- Dependency Planner
- Workflow Compiler
- Validator
- Optimizer
- Repair Planner
- Verification Engine
- Learning Engine

These become the production-grade implementation of the reasoning pipeline.