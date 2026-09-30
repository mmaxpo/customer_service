# Stage 19 — Repair Planner

Version: 0.1

---

# Purpose

The Repair Planner is the intelligence that turns failures into successful executions.

Traditional workflow engines behave like this:

```
Execution

↓

Failure

↓

Stop
```

Tajeran should behave like this:

```
Execution

↓

Verification

↓

Failure

↓

Understand Failure

↓

Repair Plan

↓

Partial Re-execution

↓

Verification

↓

Success
```

Failure is no longer the end.

It becomes another planning problem.

---

# Philosophy

A workflow should almost never fail permanently.

Instead it should continuously ask

> What is the smallest thing I need to change to reach the goal?

This makes Tajeran adaptive rather than deterministic.

---

# Repair is NOT Retry

Most systems implement

```
Retry

Retry

Retry

Retry
```

Repair is different.

Retry repeats.

Repair changes.

Example

```
Search KB

↓

No Result
```

Retry

↓

Still no result.

Repair

↓

Use Web Search.

↓

Summarize.

↓

Continue.

---

# Repair Pipeline

```
Verification Failure

↓

Analyze Failure

↓

Classify

↓

Generate Repair Plan

↓

Compile Repair Workflow

↓

Execute

↓

Verify Again
```

---

# Inputs

Repair receives

```
Original User Goal

+

Intent

+

Task Graph

+

Workflow IR

+

Execution Events

+

Verification Report

+

Runtime State

+

Available Capabilities
```

Repair never starts from scratch.

It continues from existing work.

---

# Repair Categories

Different failures require different repair strategies.

---

## Missing Information

Example

```
Refund customer.
```

Missing

```
Order Number
```

Repair

```
Ask customer.

↓

Pause workflow.

↓

Resume later.
```

---

## Tool Failure

Example

```
Shopify API timeout.
```

Repair

```
Retry

↓

Different endpoint

↓

Delayed retry

↓

Fallback provider
```

---

## Planning Error

Planner forgot

```
Read order first.
```

Repair

```
Insert

Read Order

↓

Refund
```

No need to rebuild everything.

---

## Verification Failure

Reply says

```
Refund completed.
```

Verifier

```
Refund never happened.
```

Repair

```
Replace response

↓

Generate new reply
```

---

## Policy Failure

Reply

```
Offer 100% refund
```

Policy

```
Maximum 50%
```

Repair

```
Re-plan

↓

Generate compliant response
```

---

# Repair Decision Tree

```
Failure

↓

Can retry?

↓

Yes

↓

Retry

No

↓

Can modify workflow?

↓

Yes

↓

Repair Workflow

↓

No

↓

Human Escalation
```

---

# Root Cause Analysis

Repair begins by asking

```
Why did this fail?
```

Not

```
What failed?
```

Example

```
Tool Error

↓

Authentication

↓

Expired Token
```

Repair

```
Reconnect Shopify
```

instead of

```
Retry forever
```

---

# Failure Classification

Example

```
Infrastructure

Tool

Policy

Planning

Reasoning

Knowledge

Data

Permission

Human Approval

Timeout

Rate Limit

Unexpected
```

Each class has different repair strategies.

---

# Repair Strategies

Repair chooses from

```
Retry

Replace Tool

Insert Node

Delete Node

Reorder Nodes

Split Task

Merge Tasks

Ask Human

Ask Customer

Escalate

Abort
```

---

# Partial Workflow Editing

Original

```
Read Order

↓

Refund

↓

Notify
```

Repair

```
Read Order

↓

Verify Eligibility

↓

Refund

↓

Notify
```

Only one node added.

Everything else reused.

---

# Graph-Level Repair

Repair edits

Task Graph

not Python code.

Graph transforms are much safer.

---

# Repair Operations

Supported graph operations

```
Insert Node

Delete Node

Replace Node

Reconnect Edge

Change Parameters

Add Approval

Add Verification

Split Node

Merge Nodes
```

---

# Repair Planning Output

Example

```json
{
    "strategy":"insert",

    "reason":"missing eligibility check",

    "operations":[

        {

            "insert_after":"read_order",

            "node":"check_policy"

        }

    ]
}
```

---

# Workflow Delta

Repair never generates an entire workflow if unnecessary.

It generates

```
Diff
```

Example

```
+ Policy Check

- Duplicate Search

+ Retry Limit
```

Small.

Safe.

Fast.

---

# Versioning

Every repair creates

```
Workflow Version

↓

Execution Version

↓

Verification Version
```

Everything becomes traceable.

---

# Runtime State Preservation

Repair keeps

```
Completed Nodes

Variables

Memory

Tool Results

Events
```

No reason to repeat successful work.

---

# Cached Execution

If

```
Read Order

↓

Succeeded
```

Repair should reuse

```
Order Data
```

instead of calling Shopify again.

---

# Human Repair

Some repairs require humans.

Example

```
Approve Refund
```

Repair

↓

Pause

↓

Human Approval

↓

Resume

Already supported by your runtime.

---

# Automatic Repair

Example

```
Web Search failed

↓

Knowledge Search

↓

Still failed

↓

LLM Answer

↓

Verified

↓

Success
```

No human involved.

---

# Repair Confidence

Every repair has confidence.

Example

```
0.95

Automatic

0.52

Human Review
```

---

# Repair Budget

Repair consumes

```
Tokens

Money

Time

Retries
```

Planner decides whether another repair attempt is worthwhile.

---

# Maximum Repair Depth

Example

```
Max Repairs

3
```

After that

↓

Escalate.

Never loop forever.

---

# Recursive Repair

Repair itself may fail.

Planner performs

```
Repair

↓

Verification

↓

Repair

↓

Verification
```

Until

```
Success

or

Budget Exhausted
```

---

# Repair Memory

Store

```
Repair Pattern

↓

Success Rate

↓

Future Planning
```

Eventually the planner learns

```
This repair works.

This repair never works.
```

---

# Business Repair Examples

---

## Customer Support

Problem

```
Order not found.
```

Repair

```
Ask customer

↓

Order Number
```

---

## Refund

Problem

```
Policy violation.
```

Repair

```
Offer Store Credit
```

---

## Shipping

Problem

```
Carrier unavailable.
```

Repair

```
Alternative Carrier
```

---

## CRM

Problem

```
Missing customer profile.
```

Repair

```
Lookup Email

↓

Merge Contact

↓

Continue
```

---

# Planner Interaction

Verification reports

```
Reply incomplete.
```

Repair planner receives

```
Issue

↓

Generate Fix

↓

Compile Workflow

↓

Execute
```

Execution engine never changes.

Only planning changes.

---

# Why Graph Repair Matters

If workflows are graphs

Repair becomes

```
Graph Editing
```

Instead of

```
Prompt Engineering
```

Graph editing is

- deterministic
- testable
- explainable
- reversible

Exactly what enterprise systems need.

---

# Current Tajeran Mapping

Already Exists

✅ Workflow Runtime

✅ DAG Engine

✅ Node Registry

✅ State Persistence

✅ Resume

✅ Interrupt

✅ Replay

✅ Versioned Events

Missing

❌ Repair Planner

❌ Graph Diff Engine

❌ Failure Classifier

❌ Repair Strategies

❌ Workflow Patch Generator

---

# Suggested Backend Structure

```
app/planner/repair/

    planner.py

    classifier.py

    strategies.py

    graph_editor.py

    diff.py

    validator.py

    executor.py
```

---

# APIs

```python
repair = repair_planner.plan(

    verification_report,

    workflow_ir,

    execution_state

)
```

Returns

```
WorkflowPatch
```

---

# Example

Original

```
Read KB

↓

Answer Customer
```

Verification

↓

Answer incorrect.

Repair

↓

Insert

```
Web Search
```

Workflow becomes

```
Read KB

↓

Web Search

↓

Answer Customer

↓

Verify
```

Execution continues.

---

# Long-Term Vision

```
Goal

↓

Planner

↓

Workflow

↓

Execution

↓

Verification

↓

Repair

↓

Execution

↓

Verification

↓

Repair

↓

Success
```

The system improves until the objective is reached or the repair budget is exhausted.

---

# Why This Layer Matters

Without Repair

```
AI

↓

Makes mistakes

↓

Fails
```

With Repair

```
AI

↓

Makes mistakes

↓

Learns

↓

Repairs

↓

Succeeds
```

This is the difference between an assistant and an autonomous business execution platform.

---

# MVP

Version 1

- Failure classification
- Repair planner
- Graph patch generation
- Partial workflow re-execution
- Repair history
- Retry budget

---

# Current Readiness

Execution Runtime

★★★★★

Planning Layer

★★★★☆

Verification

★★☆☆☆

Repair Planner

☆☆☆☆☆

Adaptive Workflow Editing

☆☆☆☆☆

---

# Next Investigation

## Stage 20 — Learning System

After verification and repair, Tajeran should not simply finish the task.

It should remember what happened, learn which plans succeeded or failed, improve future planning, optimize workflows, reduce token usage, and continuously become a better planner over time.

This is where the platform evolves from **adaptive** to **continuously improving**.