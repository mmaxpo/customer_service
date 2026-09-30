# Stage 33 — Planner State Machine

Version: 1.0

Status: Implementation Specification

---

# Purpose

The Planner State Machine defines the lifecycle of every planning request inside the Tajeran Cognitive Operating System.

Unlike the Workflow Runtime, which executes business workflows, the Planner Runtime executes **planning workflows**.

The planner itself becomes a deterministic state machine.

Every planning session follows the same lifecycle.

---

# Philosophy

Planning is not one LLM call.

Planning is a sequence of deterministic stages.

```
Goal

↓

Understand

↓

Reason

↓

Search

↓

Evaluate

↓

Choose

↓

Compile

↓

Execute
```

Every stage produces observable artifacts.

---

# Responsibilities

Planner State Machine owns

✓ Planning lifecycle

✓ State transitions

✓ Planning events

✓ Planning checkpoints

✓ Error recovery

✓ Planning cancellation

✓ Planning resume

Nothing else.

---

# State Diagram

```
Idle

↓

Context Collection

↓

Goal Understanding

↓

Goal Expansion

↓

Constraint Analysis

↓

Task Graph Generation

↓

Capability Search

↓

Capability Matching

↓

Candidate Plan Generation

↓

Plan Evaluation

↓

Plan Ranking

↓

Plan Selection

↓

Verification Planning

↓

Compilation

↓

Execution

↓

Completed
```

---

# High-Level Flow

```
User Prompt

↓

Planning Session Created

↓

Context Loaded

↓

Goal Understood

↓

Business Tasks Generated

↓

Capabilities Selected

↓

Candidate Plans Built

↓

Best Plan Selected

↓

Execution Graph Compiled

↓

Runtime Started

↓

Planning Finished
```

---

# State Definitions

## Idle

Purpose

No active planning.

Transitions

```
Goal Received

↓

Context Collection
```

---

## Context Collection

Planner gathers

```
Conversation

Business Memory

Knowledge

Capabilities

Policies

Constraints

User Preferences

Historical Episodes
```

Output

```
Planning Context
```

---

## Goal Understanding

Planner determines

```
Primary Goal

Secondary Goals

Expected Outcome

Success Criteria
```

Example

```
User:

Refund Sarah's damaged order.

↓

Goal

Refund Order

Outcome

Refund Completed
```

---

## Goal Expansion

Planner decomposes goals.

Example

```
Refund Customer

↓

Read Order

↓

Validate Policy

↓

Issue Refund

↓

Notify Customer
```

Produces

```
Business Task Graph
```

---

## Constraint Analysis

Planner collects constraints.

Examples

```
Budget

Latency

Compliance

Permissions

Risk

Business Policies
```

Constraints become part of planning.

---

## Task Graph Generation

Planner creates

```
Business DAG
```

No runtime nodes exist yet.

Only business tasks.

---

## Capability Search

Planner queries Capability Registry.

Example

```
Need

Refund

↓

Capabilities

Refund Order

Store Credit

Replacement
```

Produces

```
Candidate Capabilities
```

---

## Capability Matching

Planner scores every capability.

Criteria

```
Compatibility

Reliability

Latency

Cost

Business Preference

Learning Score
```

Highest ranked continue.

---

## Candidate Plan Generation

Planner creates multiple plans.

Example

```
Plan A

Knowledge

↓

Refund

Plan B

CRM

↓

Refund

Plan C

Human Review
```

Multiple plans always preferred.

---

## Plan Evaluation

Planner estimates

```
Execution Cost

Token Usage

Latency

Confidence

Risk

Verification Complexity
```

No execution yet.

---

## Plan Ranking

Planner assigns score.

Example

```
Plan A

92

Plan B

95

Plan C

81
```

Highest score wins.

---

## Plan Selection

Exactly one plan becomes active.

Output

```
Business Plan
```

Stored permanently.

---

## Verification Planning

Planner defines

```
Verification Graph

Evidence Sources

Confidence Thresholds
```

Verification exists before execution.

---

## Compilation

Business Plan

↓

Workflow Compiler

↓

Execution Graph

Planner responsibility ends.

---

## Execution

Runtime receives Execution Graph.

Planner becomes observer.

Planner waits for

```
Verification

Repair

Learning
```

---

## Completed

Planning Session archived.

Produces

```
Plan

Metrics

Events

Timing

Statistics

Episode
```

---

# State Transition Rules

Every transition has

```
Entry Conditions

Exit Conditions

Timeout

Failure Policy

Recovery Policy
```

Transitions are deterministic.

---

# Planning Interruptions

Planner may pause.

Reasons

```
Need Human Input

Missing Capability

Ambiguous Goal

Policy Conflict
```

Resume later.

---

# Failure States

Planning failures include

```
Context Failure

Goal Failure

Capability Failure

Compilation Failure

Policy Failure

Timeout
```

Planner never crashes silently.

---

# Planning Resume

Planner resumes from checkpoints.

Example

```
Capability Search

↓

Crash

↓

Resume

Capability Search
```

No restart required.

---

# Planning Cancellation

Planner supports

```
User Cancel

Timeout

Business Rule

Administrator

System Shutdown
```

Produces

```
PlanningCancelled Event
```

---

# Planner Events

Every transition emits events.

```
PlanningStarted

ContextCollected

GoalExpanded

TaskGraphCreated

CapabilitiesMatched

CandidatePlansCreated

PlanSelected

VerificationPlanned

CompilationStarted

PlanningCompleted
```

Everything observable.

---

# Planner Checkpoints

Planner snapshots after

```
Context

Goal

Tasks

Capabilities

Candidate Plans

Selected Plan

Compilation
```

Allows replay.

---

# Planner Metrics

Collected automatically.

```
Planning Time

LLM Calls

Token Usage

Candidate Plans

Capabilities Evaluated

Confidence

Compilation Time
```

---

# Planner APIs

```
create_session()

resume()

cancel()

current_state()

history()

events()
```

---

# Backend Structure

```
app/planner/runtime/

    state_machine.py

    states.py

    transitions.py

    checkpoints.py

    events.py

    lifecycle.py

    metrics.py

    session.py
```

---

# Integration With Existing Runtime

Current Runtime

```
Execution Runtime
```

New

```
Planner Runtime

↓

Workflow Compiler

↓

Execution Runtime
```

Two runtimes.

One for thinking.

One for execution.

---

# Existing Tajeran Mapping

Already Exists

★★★★★ Execution Runtime

★★★★★ Runtime Events

★★★★★ Runtime Persistence

★★★★★ Resume Logic

Needs Implementation

☆☆☆☆☆

Planner Runtime

☆☆☆☆☆

Planner State Machine

☆☆☆☆☆

Planner Checkpoints

☆☆☆☆☆

Planner Lifecycle

---

# Engineering Principle

The Planner should be just as deterministic, observable and replayable as the Workflow Runtime.

Planning itself is a workflow.

---

# Next Stage

## Stage 34 — Planner Internal Data Model

The next stage defines every object stored inside the Planner Runtime.

Planner State

Planning Context

Business Goal

Candidate Plan

Planning Metrics

Planning Events

Confidence Objects

Planner Session

These objects become the internal language of the Planner.