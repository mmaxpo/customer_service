# Stage 37 — Goal Decomposition Engine

Version: 1.0

Status: Implementation Specification

---

# Purpose

The Goal Decomposition Engine transforms high-level business goals into executable business tasks.

The Planner never plans directly from a user's goal.

Instead it progressively decomposes goals until every remaining task is atomic, measurable, and executable.

This engine creates the Planner's Business Task Graph.

---

# Philosophy

Humans think in goals.

Execution thinks in actions.

The Goal Decomposition Engine bridges those worlds.

```
Business Goal

↓

Sub Goals

↓

Business Tasks

↓

Atomic Tasks

↓

Business Task Graph
```

Planning starts only after decomposition.

---

# Core Principle

Every task produced by this engine must answer

```
Can one capability solve this?

YES

↓

Atomic Task

NO

↓

Decompose Again
```

The planner never executes non-atomic business tasks.

---

# Responsibilities

The Goal Decomposition Engine owns

✓ Goal hierarchy

✓ Recursive decomposition

✓ Task creation

✓ Dependency discovery

✓ Parallel task discovery

✓ Complexity estimation

✓ Completion criteria

Nothing else.

---

# Pipeline

```
Business Intent

↓

Business Goals

↓

Goal Analysis

↓

Recursive Decomposition

↓

Atomic Task Detection

↓

Dependency Analysis

↓

Business Task Graph

↓

Planner
```

---

# Input

Consumes

```python
BusinessIntent

Primary Goal

Secondary Goals

Constraints

Entities

Planning Context
```

---

# Output

Produces

```python
BusinessTaskGraph

tasks

dependencies

entry_tasks

exit_tasks

parallel_groups

critical_path
```

---

# Goal Hierarchy

Goals are hierarchical.

Example

```
Resolve Customer Issue

↓

Refund Customer

↓

Issue Refund

↓

Notify Customer

↓

Update CRM
```

Each child contributes toward parent completion.

---

# Goal Object

```python
BusinessGoal

id

title

description

priority

parent

children

constraints

success_conditions

status
```

Goals remain business-oriented.

---

# Atomic Task Definition

An Atomic Task satisfies four conditions.

```
One responsibility

One measurable outcome

One capability owner

One verification strategy
```

If any condition fails

↓

Further decomposition.

---

# Examples

High-level Goal

```
Resolve Support Request
```

Atomic Tasks

```
Read Conversation

Detect Intent

Retrieve Order

Check Policy

Prepare Response

Notify Customer
```

Each task can be solved independently.

---

# Recursive Decomposition

Planner decomposes until every task is atomic.

```
Refund Customer

↓

Validate Customer

↓

Retrieve Order

↓

Check Refund Policy

↓

Create Refund

↓

Notify Customer
```

Depth varies by problem.

---

# Decomposition Strategies

Planner supports multiple strategies.

```
Rule-based

Capability-based

Template-based

LLM-assisted

Learning-assisted
```

Strategy chosen dynamically.

---

# Rule-Based Decomposition

Simple goals.

Example

```
Refund

↓

Policy

↓

Refund

↓

Notify
```

Fast.

Deterministic.

---

# Capability-Based Decomposition

Planner asks

```
Can one capability solve this?

↓

No

↓

Split Goal
```

Produces better atomicity.

---

# Template-Based Decomposition

Known business processes.

Example

```
Refund

↓

Standard Refund Template
```

Reusable.

---

# LLM-Assisted Decomposition

Only used when deterministic strategies fail.

LLM suggests candidate task hierarchies.

Planner validates them.

LLM never owns decomposition.

---

# Learning-Assisted Decomposition

Learning Engine recommends

```
Previous Successful Task Graphs
```

Planner reuses proven structures.

---

# Task Categories

```
Information

Decision

Validation

Business Action

Communication

Approval

Verification

Observation
```

Every task has exactly one category.

---

# Task Object

```python
BusinessTask

id

title

description

category

priority

complexity

estimated_duration

required_capabilities

dependencies

verification_requirements
```

---

# Dependency Discovery

Planner discovers ordering.

Example

```
Retrieve Order

↓

Check Policy

↓

Issue Refund

↓

Notify Customer
```

Dependencies become DAG edges.

---

# Parallel Task Discovery

Independent tasks execute together.

Example

```
Read Customer

Read Conversation

Read Order
```

Planner marks

```
Parallel Group 1
```

Compiler later parallelizes.

---

# Complexity Estimation

Every task receives

```
Complexity

Low

Medium

High

Very High
```

Used during planning.

---

# Cost Estimation

Task estimates

```
Execution Time

Token Cost

API Calls

Business Cost
```

Before execution.

---

# Success Conditions

Every task defines

```
Done when...
```

Example

```
Issue Refund

↓

Refund ID Exists
```

Verification later consumes these.

---

# Failure Conditions

Every task also defines

```
Failure when...

Timeout

Policy Violation

Capability Missing

Verification Failed
```

Repair uses these later.

---

# Goal Completion

Parent goal automatically completes when

```
All Required Children Complete
```

Supports partial completion.

---

# Optional Tasks

Some tasks are optional.

Example

```
Customer Feedback

Optional

Does not block workflow.
```

Planner tracks importance.

---

# Critical Tasks

Some tasks are mandatory.

```
Refund

Policy Check

Verification
```

Cannot be skipped.

---

# Goal Graph Validation

Engine validates

```
No Cycles

No Orphans

Valid Dependencies

Reachable Exit

Connected Graph
```

Before returning.

---

# Graph Metrics

Collected automatically.

```
Task Count

Depth

Width

Critical Path

Parallel Groups

Estimated Duration
```

Useful for optimization.

---

# Events

Engine emits

```
GoalsCreated

GoalExpanded

TaskCreated

DependenciesFound

ParallelGroupsDetected

TaskGraphCompleted
```

Everything observable.

---

# APIs

```python
decompose()

expand_goal()

create_tasks()

discover_dependencies()

detect_parallelism()

validate_graph()

estimate_complexity()
```

Planner uses

```
build_task_graph()
```

---

# Suggested Backend Structure

```
app/planner/decomposition/

    engine.py

    hierarchy.py

    decomposition.py

    atomicity.py

    dependencies.py

    parallelism.py

    validation.py

    complexity.py

    metrics.py

    events.py
```

---

# Existing Tajeran Mapping

Already Exists

★★★★★ DAG Runtime

★★★★★ Workflow Graph

★★★★★ Node Dependencies

★★★★☆ Runtime Graph Validation

Needs Implementation

☆☆☆☆☆

Goal Decomposition

☆☆☆☆☆

Business Task Graph

☆☆☆☆☆

Atomic Task Detection

☆☆☆☆☆

Planning Metrics

---

# Engineering Principle

The Planner never plans from goals.

It plans from atomic business tasks.

Everything else is decomposition.

---

# Long-Term Vision

As TCOS evolves, the Goal Decomposition Engine becomes reusable across every domain.

Customer Service

↓

Business Tasks

Sales

↓

Business Tasks

ERP

↓

Business Tasks

Security

↓

Business Tasks

The Planner always operates on the same abstraction.

---

# Next Stage

## Stage 38 — Dependency & Constraint Analysis Engine

Once the Business Task Graph has been created, the Planner must understand:

- which tasks depend on others,
- which tasks may execute in parallel,
- which business constraints limit execution,
- where bottlenecks exist,
- what the critical path is,
- what risks exist before execution begins.

This engine transforms a task list into an optimized planning graph before capability matching begins.