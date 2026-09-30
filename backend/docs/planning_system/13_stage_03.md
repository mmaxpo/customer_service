# Stage 03 — Capability Dependency Graph

Version: 0.1

---

# Purpose

Capabilities never exist alone.

Every capability depends on:

- data
- previous work
- permissions
- context
- business state

The planner must understand these relationships before it can generate reliable workflows.

Instead of asking

> "Which capability can do this?"

the planner begins asking

> "What sequence of capabilities produces this business outcome?"

This document defines those relationships.

---

# From Capabilities to Graphs

Instead of viewing capabilities as a list

```
Refund Order

Knowledge Search

Generate Reply

Approval

Shipping Status
```

the planner views them as

```
Customer asks

↓

Understand request

↓

Read order

↓

Evaluate policy

↓

Decide action

↓

Need approval?

↓

Execute action

↓

Generate reply
```

That is a dependency graph.

---

# Graph Types

Tajeran primarily contains five kinds of dependency.

---

## Sequential

```
A

↓

B

↓

C
```

Example

```
Read Order

↓

Determine Refund Eligibility

↓

Create Refund
```

---

## Parallel

```
      Search KB

      /

Customer

      \

Read Order
```

Independent work executed simultaneously.

---

## Decision

```
Read Order

↓

Refund Eligible?

↓

YES          NO

↓

Refund     Explain Policy
```

---

## Human Gate

```
Refund

↓

Approval

↓

Execute Refund
```

---

## Loop

```
Plan

↓

Execute

↓

Verify

↓

Repair

↓

Done
```

The planner will eventually build these automatically.

---

# Runtime Dependency Graph

---

## Workflow Execution

```
Trigger

↓

Router

↓

Nodes

↓

Response
```

Dependencies

Trigger required first.

Response always last.

---

## Agent Execution

```
Input

↓

System Prompt

↓

Planner

↓

LLM

↓

Tools

↓

Result
```

Dependencies

Tool calling depends on

- LLM

Tool execution depends on

- registry

Approval depends on

- tool metadata

---

## Human Approval

```
Tool Call

↓

Approval Request

↓

Pause

↓

Resume

↓

Continue
```

Already implemented.

---

# Customer Service Graph

Current capability graph

```
Conversation

↓

Intent

↓

Knowledge Search

↓

Reply Generation

↓

Customer Reply
```

Future

```
Conversation

↓

Intent

↓

Sentiment

↓

Risk

↓

Knowledge

↓

Decision

↓

Reply

↓

Verification

↓

Send
```

---

# Commerce Graph

Refund

```
Customer Request

↓

Read Order

↓

Eligibility

↓

Approval

↓

Refund

↓

Notify Customer
```

Dependencies

```
Refund

depends on

↓

Order

↓

Connection

↓

Permissions

↓

Approval
```

---

Shipping Update

```
Customer Request

↓

Read Order

↓

Validate Address

↓

Approval

↓

Update Address

↓

Notify
```

---

Cancel Order

```
Request

↓

Read Order

↓

Cancellation Rules

↓

Approval

↓

Cancel

↓

Reply
```

---

# Knowledge Graph

```
Question

↓

Knowledge Search

↓

Retrieve Documents

↓

Summarize

↓

Return Context
```

Future

```
Question

↓

Multiple Sources

↓

Ranking

↓

Compression

↓

Verification

↓

Context
```

---

# Planner Graph

Planner itself becomes a graph.

```
Prompt

↓

Intent

↓

Requirements

↓

Capability Discovery

↓

Graph Generation

↓

Validation

↓

Optimization

↓

Execution
```

Notice

Planner never jumps directly to execution.

---

# Capability Relationships

## Generate Reply

Depends on

```
Conversation

Knowledge

Policies

Decision
```

---

## Refund

Depends on

```
Order

Eligibility

Approval

Shopify
```

---

## Knowledge Search

Depends on

```
Knowledge Store

Embedding

Retriever
```

---

## Tool Call

Depends on

```
Planner

Registry

Permission

Arguments
```

---

## Workflow Execution

Depends on

```
Graph

Runtime

Persistence

Event Store
```

---

# Shared Dependencies

Many capabilities require identical prerequisites.

Example

```
Refund

Cancel

Shipping Update

Reship
```

all require

```
Read Order
```

Planner learns this once.

---

Another

```
Reply

Summary

Classification

Decision
```

all require

```
Conversation Context
```

Again,

one dependency,

many capabilities.

---

# Composite Capabilities

Eventually the planner no longer exposes

```
Refund

Approval

Reply
```

Instead it discovers

```
Handle Refund Request
```

which expands into

```
Read Order

↓

Eligibility

↓

Approval

↓

Refund

↓

Generate Reply
```

Composite capabilities become reusable planning templates.

---

# Capability Graph Database

Planner eventually builds an internal graph.

Example

```
Capability

↓

Requires

↓

Produces

↓

Consumes

↓

Permissions

↓

Risk

↓

Cost

↓

Average Duration

↓

Confidence
```

Example node

```
refund.create

requires

order

approval

shopify connection

produces

refund_id

customer_notification
```

This becomes searchable.

---

# Automatic Composition

Planner receives

```
Customer wants refund.
```

Planner graph search

```
Goal

↓

refund.create

↓

needs order

↓

needs approval

↓

needs reply

↓

workflow complete
```

Workflow generated automatically.

---

# Missing Dependency Knowledge

Current backend knows

```
How to execute
```

Current backend does NOT know

```
How capabilities depend on each other.
```

That is exactly what this stage adds.

---

# Graph Validation

Every generated graph will be checked.

Questions

```
Missing input?

Missing approval?

Circular dependency?

Impossible execution?

Unknown capability?

Permission issue?

Tool unavailable?

Duplicate work?
```

Planner fixes graph before execution.

---

# Runtime Mapping

Planner Graph

↓

Business Graph

↓

Workflow Graph

↓

Runtime DAG

↓

Execution Engine

↓

Events

↓

Verification

↓

Repair

↓

Finished

Notice

Planner never directly builds runtime nodes.

It first builds a business graph.

Only then converts into runtime DAG.

---

# Future Capability Learning

Eventually planner will learn

```
Thousands of successful executions.

↓

Common patterns.

↓

Best workflow.

↓

Shorter workflow.

↓

Lower token workflow.

↓

Higher confidence workflow.
```

Planner improves without changing runtime.

---

# Current Readiness

Execution Runtime

★★★★★

Capability Inventory

★★★★☆

Dependency Knowledge

★☆☆☆☆

Planner

☆☆☆☆☆

Workflow Generation

☆☆☆☆☆

This document defines the missing layer between capability inventory and intelligent planning.

---

# Next Investigation

Stage 04

Business Object Model

The planner cannot reason only about capabilities.

It must understand the objects those capabilities manipulate.

Examples

Customer

Conversation

Order

Ticket

Knowledge

Workflow

Agent

Approval

Tool

These become the planner's vocabulary.

Without this vocabulary, planning remains shallow.

With it, the planner begins reasoning about business rather than code.