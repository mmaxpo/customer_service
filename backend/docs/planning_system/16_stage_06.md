# Stage 06 — Planner Memory Model

Version: 0.1

---

# Purpose

Planning is not a single LLM call.

Planning is a reasoning process.

Every reasoning process requires memory.

Without memory

```
Prompt

↓

LLM

↓

Answer
```

With memory

```
Prompt

↓

Planner

↓

Working Memory

↓

Capability Memory

↓

Decision Memory

↓

Execution Memory

↓

Verification Memory

↓

Answer
```

This document defines every memory layer inside the Tajeran Planning System.

---

# Core Principle

Memory is not conversation history.

Memory is structured knowledge created while planning.

The planner should remember

- what it knows
- what it decided
- what it tried
- what succeeded
- what failed
- why

---

# Memory Layers

The planner contains six independent memory systems.

```
Working Memory

Capability Memory

Decision Memory

Execution Memory

Verification Memory

Experience Memory
```

Each solves a different problem.

---

# 1. Working Memory

Purpose

Represents the planner's current thoughts.

Equivalent to

```
Architect's whiteboard.
```

Contains

```
Current Goal

Business Objects

Intent

Constraints

Current Graph

Missing Information

Open Questions

Assumptions
```

Example

```
Goal

Refund order

Known

Customer

Order

Unknown

Refund amount

Approval

Next Task

Read Order
```

Working memory is temporary.

Destroyed after planning.

---

# Working Memory Structure

```
Goal

Objects

Capabilities

Graph

Variables

Open Tasks

Completed Tasks

Current Step

Confidence
```

Planner updates it continuously.

---

# 2. Capability Memory

Purpose

Remember everything the platform knows how to do.

Contains

```
Capabilities

Requirements

Inputs

Outputs

Risk

Cost

Average Success

Average Duration

Dependencies
```

Example

```
refund.create

↓

Needs

Order

Approval

↓

Produces

Refund
```

Capability Memory changes slowly.

---

# 3. Decision Memory

Purpose

Remember why decisions were made.

Example

Planner chooses

```
Refund

instead of

Replacement
```

Decision Memory stores

```
Reason

↓

Policy says

↓

Inventory unavailable

↓

Customer requested refund
```

Future reasoning uses this.

---

# Decision Record

```
Decision

Reason

Confidence

Evidence

Alternatives

Timestamp
```

Planner can explain itself later.

---

# 4. Execution Memory

Purpose

Track execution state.

Contains

```
Workflow Run

Agent Runs

Completed Steps

Failures

Outputs

Tool Calls

Interrupts

Retries
```

Example

```
Read Order

✓

Knowledge Search

✓

Refund

Waiting Approval
```

Planner never repeats completed work.

---

# Execution Graph

```
Node

↓

Started

↓

Finished

↓

Result

↓

Duration

↓

Usage

↓

Status
```

Execution memory already exists in your backend.

It only needs planner integration.

---

# 5. Verification Memory

Purpose

Remember verification results.

Planner asks

```
Was the result correct?
```

Stores

```
Checks

Policy Validation

Tool Validation

Output Validation

Customer Validation
```

Example

```
Reply Generated

↓

Verified

↓

Policy Passed

↓

Safe
```

---

# Verification Record

```
Target

Validation

Result

Confidence

Issues

Repair Needed
```

Planner learns from failures.

---

# 6. Experience Memory

Purpose

Long-term learning.

Stores

```
Successful Plans

Failed Plans

Common Patterns

Frequently Used Capabilities

Optimization Data
```

Example

Planner learns

```
Refund workflows

Usually require

Read Order

↓

Approval

↓

Reply
```

Next time

Planning becomes faster.

---

# Memory Lifetime

Working Memory

```
Minutes
```

Execution Memory

```
Hours

Days
```

Decision Memory

```
Permanent
```

Capability Memory

```
Permanent
```

Experience Memory

```
Forever
```

---

# Memory Ownership

Working Memory

Owned by Planner.

Execution Memory

Owned by Runtime.

Capability Memory

Owned by Capability Registry.

Decision Memory

Owned by Planner.

Experience Memory

Owned by Learning System.

---

# Memory Flow

Prompt

↓

Working Memory

↓

Planner

↓

Execution

↓

Execution Memory

↓

Verification

↓

Verification Memory

↓

Experience Memory

Planner becomes smarter every execution.

---

# Working Memory Example

Prompt

```
Customer wants refund.
```

Working Memory

```
Goal

Refund

Objects

Customer

Conversation

Order

Known

Intent

Unknown

Refund Eligibility

Missing

Order

Next

Read Order
```

Planner updates this continuously.

---

# Execution Memory Example

```
Workflow

↓

Read Order

✓

↓

Policy Check

✓

↓

Approval

Waiting

↓

Refund

Not Started
```

Planner resumes correctly after interruption.

---

# Experience Memory Example

Planner has seen

```
Refund

27,000 times
```

Learns

```
Best sequence

↓

Read Order

↓

Eligibility

↓

Approval

↓

Refund

↓

Reply
```

Planning improves automatically.

---

# Planner Context

Planner never sends raw conversation history.

Instead it sends structured memory.

Example

```
Goal

Refund

Objects

Customer

Order

Capabilities

Read Order

Refund

Reply

Current Graph

...

Missing

Approval
```

Much smaller.

Much cheaper.

Much more accurate.

---

# Memory Compression

Large executions cannot fit in context.

Planner compresses.

```
200 Events

↓

Summary

↓

12 Important Facts

↓

Continue Planning
```

Compression preserves reasoning.

---

# Memory Search

Planner searches memory.

Example

```
Need capability

↓

Search Capability Memory

↓

Found

refund.create
```

Need previous plan

↓

Search Experience Memory

↓

Found similar workflow

Reuse.

---

# Mapping to Backend

Current Backend

Already Contains

```
Workflow State

Workflow Events

Agent State

Agent Events

Snapshots

Persistence

Replay

Timeline
```

Missing

```
Working Memory

Decision Memory

Capability Memory

Experience Memory
```

Execution Memory already exists.

---

# Future Learning

Planner eventually records

```
100,000 Plans

↓

Best Practices

↓

Automatic Optimization

↓

Planning Heuristics

↓

Business Patterns
```

This becomes Tajeran's intelligence.

Not the LLM.

---

# Current Readiness

Execution Memory

★★★★★

Workflow Persistence

★★★★★

Replay

★★★★★

Agent State

★★★★★

Working Memory

☆☆☆☆☆

Decision Memory

☆☆☆☆☆

Capability Memory

☆☆☆☆☆

Experience Memory

☆☆☆☆☆

---

# Target Architecture

Prompt

↓

Working Memory

↓

Planner

↓

Capability Memory

↓

Decision Memory

↓

Execution

↓

Execution Memory

↓

Verification

↓

Verification Memory

↓

Experience Memory

↓

Continuous Improvement

Every execution makes the planner smarter.

---

# Why This Stage Matters

Most AI systems forget everything after one response.

Tajeran should become a system that accumulates operational intelligence.

It doesn't just answer.

It learns how businesses operate.

---

# Next Investigation

Stage 07

Planner Reasoning Pipeline

Now that the planner has:

- Business Objects
- Capability Ontology
- Dependency Graph
- Memory

we can define **how it actually thinks**.

This will describe the complete cognitive pipeline from:

Prompt

↓

Intent

↓

Understanding

↓

Planning

↓

Validation

↓

Optimization

↓

Execution

↓

Verification

↓

Repair

↓

Result

This is the heart of the Tajeran Planning System.