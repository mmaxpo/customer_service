# Stage 30 — Repair Engine

Version: 0.1

Status: Cognitive Core

---

# Purpose

The Repair Engine automatically recovers from failures without restarting the entire workflow.

Execution executes.

Verification proves.

Repair adapts.

This is one of the defining capabilities of an autonomous system.

---

# Philosophy

Most systems

```
Failure

↓

Retry

↓

Failure

↓

Human
```

Tajeran

```
Failure

↓

Diagnosis

↓

Repair Plan

↓

Partial Replanning

↓

Resume Execution

↓

Verification
```

Repair is intelligent.

Not repetitive.

---

# Core Principle

Failures are not exceptions.

Failures are information.

Every failure teaches the planner something about reality.

---

# Repair Pipeline

```
Execution

↓

Verification Failed

↓

Collect Evidence

↓

Root Cause Analysis

↓

Repair Planning

↓

Graph Rewrite

↓

Resume

↓

Verification
```

Execution never starts over unless absolutely necessary.

---

# Responsibilities

Repair Engine owns

✓ Failure diagnosis

✓ Root cause analysis

✓ Partial replanning

✓ Capability replacement

✓ Runtime patching

✓ Retry policy

✓ Human escalation

Nothing else.

---

# Repair Levels

Level 1

Retry

Example

```
Timeout

↓

Retry
```

---

Level 2

Parameter Repair

Example

```
Wrong Order ID

↓

Lookup Correct Order
```

---

Level 3

Capability Replacement

Example

```
Provider A Failed

↓

Provider B
```

---

Level 4

Graph Rewrite

Example

```
Missing Customer

↓

Insert Customer Lookup

↓

Resume
```

---

Level 5

Planner Replan

Planner generates an entirely new business plan.

Only used when required.

---

# Repair Objects

```
RepairRequest

↓

FailureAnalysis

↓

RepairPlan

↓

RepairGraph

↓

RepairExecution

↓

RepairResult
```

---

# Failure Analysis

Every failure becomes structured.

Never generic exceptions.

---

Example

```python
Failure

type

ToolFailure

reason

Shopify timeout

severity

Medium

retryable

True

confidence

0.94
```

---

# Failure Categories

```
Runtime

Tool

Business

Policy

Permission

Network

Security

Data

Planning

Verification
```

Each category has different repair strategies.

---

# Root Cause Analysis

Repair never asks

"What failed?"

Repair asks

"Why?"

Example

```
Refund Failed

↓

Order Locked

↓

Inventory Sync Running
```

Now repair has context.

---

# Repair Strategies

Example

```
Retry

↓

Wait

↓

Alternative Capability

↓

Alternative Provider

↓

Replan

↓

Human
```

Chosen dynamically.

---

# Retry Policy

Retries are not blind.

Each retry has

```
Maximum Attempts

Backoff

Conditions

Timeout

Escalation
```

---

# Capability Replacement

Planner may choose another capability.

Example

```
Search Knowledge

↓

Vector Search Failed

↓

Hybrid Search
```

Business plan remains identical.

---

# Provider Replacement

Example

```
SMTP Failed

↓

SES

↓

Resend
```

Automatic failover.

---

# Partial Graph Repair

Current graph

```
A

↓

B

↓

C

↓

D
```

Failure

```
C
```

Repair graph

```
A

↓

B

↓

Repair

↓

C'

↓

D
```

No restart.

---

# Dynamic Node Injection

Repair may insert runtime nodes.

Example

```
Lookup Customer

↓

Retry Refund
```

Compiler creates only required patch.

---

# Graph Rewriting

Repair modifies

Business Graph

Capability Graph

Execution Graph

Depending on failure type.

---

# Planner Collaboration

Repair asks planner only when necessary.

```
Simple Failure

↓

Repair Engine

Complex Failure

↓

Planner
```

Planner is expensive.

Repair is lightweight.

---

# Human Escalation

Repair decides when humans are required.

Example

```
Three Failed Repairs

↓

Escalate
```

Not immediately.

---

# Repair Budget

Repair has limits.

```
Maximum Time

Maximum Cost

Maximum Attempts

Maximum Graph Size
```

Repair must terminate.

---

# Repair Confidence

Repair also estimates confidence.

```
Repair Success

0.93

↓

Execute
```

---

# Repair Graph

Repair itself becomes a graph.

```
Diagnose

↓

Choose Strategy

↓

Patch Workflow

↓

Resume

↓

Verify
```

Everything observable.

---

# Repair History

Every repair stored.

```
Failure

↓

Repair

↓

Outcome

↓

Lesson
```

Learning consumes this.

---

# Learning Integration

Planner later discovers

```
Repair A

Succeeded

98%

↓

Prefer A
```

Continuous optimization.

---

# Memory Integration

Repair reads

```
Previous Repairs

Similar Failures

Customer Context

Execution History

Business Rules
```

Never repairs blindly.

---

# Runtime Integration

Repair can

Resume Workflow

Patch Variables

Insert Nodes

Replace Capabilities

Restart Subgraph

Never restart entire workflow unless necessary.

---

# Repair Events

```
FailureDetected

DiagnosisStarted

RepairSelected

GraphPatched

ExecutionResumed

RepairSucceeded

RepairFailed
```

Everything observable.

---

# Repair API

```python
repair()

diagnose()

patch_graph()

replace_capability()

resume()

escalate()
```

Planner never repairs directly.

---

# Suggested Backend Structure

```
app/repair/

    engine.py

    diagnosis.py

    planner_bridge.py

    graph_patch.py

    strategies/

    history.py

    confidence.py

    escalation.py

    events.py
```

---

# Existing Tajeran Mapping

Already Exists

★★★★★ Resume

★★★★★ Interrupts

★★★★★ Runtime State

★★★★★ Workflow Persistence

★★★★★ Event Stream

Needs Implementation

☆☆☆☆☆

Repair Engine

☆☆☆☆☆

Root Cause Analyzer

☆☆☆☆☆

Graph Patcher

☆☆☆☆☆

Capability Replacement

☆☆☆☆☆

Repair Planner

---

# Engineering Principle

Never restart a workflow if only 5% of it failed.

Repair only the broken portion.

Exactly like modern operating systems.

---

# Long-Term Vision

Execution

↓

Verification

↓

Repair

↓

Learning

↓

Future executions become more reliable.

Autonomy increases naturally.

---

# Readiness

Runtime

★★★★★

Verification

★★☆☆☆

Repair

☆☆☆☆☆

Importance

★★★★★

---

# Next Stage

## Stage 31 — Learning Engine

Everything until now has focused on solving the current problem.

The Learning Engine focuses on improving the next thousand problems.

Instead of retraining models, Tajeran continuously improves:

- planning
- capability selection
- graph optimization
- repair strategies
- verification confidence
- execution efficiency

The platform itself becomes progressively more capable through experience.