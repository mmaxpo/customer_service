# Business Task Graph
**Version:** 0.1 (Architecture Draft)

---

# Vision

The Business Task Graph (BTG) is the core planning language of Tajeran.

It is **not** a workflow.

It is **not** a DAG.

It is **not** runtime nodes.

It is **not** an LLM prompt.

It is a technology-independent description of the business work required to achieve a goal.

```
User Goal

↓

Business Task Graph

↓

Capability Resolution

↓

Workflow IR

↓

Runtime DAG
```

The Business Task Graph is the bridge between human goals and executable workflows.

---

# Why Business Task Graph Exists

Traditional workflow systems ask:

> "What nodes should execute?"

Traditional LLM systems ask:

> "What should the model do?"

Tajeran asks a different question:

> **"What business work must be completed?"**

Everything else is implementation.

---

# Design Principles

The BTG must remain completely independent of:

- LLM providers
- Runtime engine
- Workflow nodes
- APIs
- Databases
- Programming languages
- Infrastructure

The BTG describes **business work**, not technical work.

---

# Pipeline Position

```
User Prompt

↓

Intent

↓

Goal

↓

Business Task Graph

↓

Capability Resolver

↓

Workflow IR

↓

Runtime DAG

↓

Execution
```

Planning ends with the Business Task Graph.

Execution begins after Workflow IR.

---

# Definition

A Business Task represents one meaningful unit of business work.

It answers:

> "What needs to happen?"

It never answers:

> "How should it happen?"

---

# Business Task Rules

## Rule 1

One responsibility.

Good

```
Read Customer Order
```

Bad

```
Read Order and Refund Customer
```

---

## Rule 2

Business language only.

Good

```
Generate Customer Reply
```

Bad

```
Call GPT
```

---

## Rule 3

Technology independent.

Good

```
Check Refund Eligibility
```

Bad

```
Execute Shopify GraphQL Query
```

---

## Rule 4

Produces business value.

Good

```
Verify Customer Identity
```

Bad

```
Serialize JSON
```

---

## Rule 5

Can later map to one or many capabilities.

Example

```
Read Order
```

might become

- Shopify
- WooCommerce
- Magento
- SAP
- Oracle

without changing planning.

---

# Business Task Categories

Every business task belongs to one category.

## Read

Examples

```
Read Conversation

Read Customer

Read Order

Read Policy

Read Inventory
```

---

## Analyze

Examples

```
Determine Intent

Evaluate Sentiment

Detect Fraud

Assess Risk

Calculate Priority
```

---

## Decide

Examples

```
Approve Refund

Select Shipping Method

Assign Agent

Choose Workflow
```

---

## Execute

Examples

```
Create Refund

Cancel Order

Update Address

Assign Ticket

Create Invoice
```

---

## Generate

Examples

```
Generate Reply

Generate Summary

Generate Report

Generate Knowledge Article
```

---

## Verify

Examples

```
Verify Refund

Verify Payment

Verify Policy Compliance

Verify Goal Completion
```

---

## Notify

Examples

```
Notify Customer

Notify Manager

Notify Team

Publish Event
```

---

## Record

Examples

```
Create Audit Record

Store Conversation Summary

Record Decision

Update Timeline
```

---

# Graph Structure

Business Tasks form a directed graph.

Example

```
Read Conversation
        │
        ▼
Read Order
        │
        ▼
Check Refund Policy
        │
        ▼
Evaluate Eligibility
      ╱     ╲
     ▼       ▼
Refund     Reject
      ╲     ╱
        ▼
Generate Reply
        │
        ▼
Update Conversation
```

Notice

No runtime nodes exist.

Only business work.

---

# Business Task Object

Example

```json
{
  "task_id": "read_order",
  "type": "Read",
  "name": "Read Order",
  "description": "Retrieve order information for the customer.",
  "depends_on": [
      "read_conversation"
  ],
  "required_capabilities": [
      "order.read"
  ],
  "goal": "Resolve Refund Request"
}
```

Notice

No APIs.

No tools.

No nodes.

---

# Example 1 — Customer Service

Goal

```
Resolve Refund Request
```

Business Task Graph

```
Read Conversation

↓

Read Order

↓

Check Refund Policy

↓

Evaluate Eligibility

↓

Generate Customer Reply

↓

Update Conversation

↓

Record Audit
```

---

# Example 2 — Shopify

Goal

```
Provide Shipping Status
```

Business Task Graph

```
Read Conversation

↓

Read Order

↓

Read Shipment

↓

Generate Reply

↓

Notify Customer
```

---

# Example 3 — HR

Goal

```
Onboard Employee
```

Business Task Graph

```
Collect Employee Information

↓

Create Accounts

↓

Assign Equipment

↓

Grant Permissions

↓

Schedule Orientation

↓

Notify Employee
```

---

# Example 4 — Security

Goal

```
Rotate AWS Credentials
```

Business Task Graph

```
Read Existing Credential

↓

Generate Credential

↓

Deploy Credential

↓

Verify Deployment

↓

Audit Change

↓

Notify Team
```

---

# Planner Responsibilities

The Planner owns Business Task creation.

Responsibilities

- Understand intent
- Understand goal
- Build BTG
- Estimate complexity
- Identify dependencies
- Produce deterministic task graph

The Planner does **not**

- choose runtime nodes
- call APIs
- execute tools
- manage state
- retry failures

---

# Runtime Responsibilities

The Runtime never sees the user prompt.

The Runtime receives Workflow IR.

Responsibilities

- Execute
- Retry
- Resume
- Persist
- Wait
- Schedule
- Replay
- Cancel

The Runtime does **not**

- understand business goals
- generate tasks
- reason about planning

---

# Why This Layer Exists

Without BTG

```
Prompt

↓

LLM

↓

Workflow
```

Planning becomes coupled to execution.

With BTG

```
Prompt

↓

Planner

↓

Business Task Graph

↓

Capability Resolver

↓

Workflow Compiler

↓

Runtime
```

Every layer has exactly one responsibility.

---

# Advantages

## Explainability

Planner can explain

```
"I chose these business tasks because..."
```

---

## Determinism

Compilation becomes deterministic.

No additional reasoning required.

---

## Testing

Business Task Graphs can be unit tested independently.

---

## Provider Independence

Replacing Shopify with Magento changes only capability mappings.

Business Tasks remain unchanged.

---

## Lower Token Usage

The LLM reasons once.

Compilation is deterministic.

---

## Multi-Product Platform

Exactly the same Planner can create BTGs for:

- Customer Service
- CRM
- HR
- ERP
- Security
- PAM
- Sales
- Internal Automation

Only capabilities change.

---

# Current Tajeran Assessment

Current Runtime

≈95%

Current Agent Runtime

≈90%

Current Business Task Graph

≈5%

This layer does not yet exist and becomes the first major addition to the planning architecture.

---

# Relationship to Other Architecture Documents

Previous

```
01_tajeran_planning_system.md
```

↓

Current

```
02_business_task_graph.md
```

↓

Next

```
03_capability_resolver.md
```

---

# Long-Term Vision

Business Tasks become the universal language of work inside Tajeran.

The Planner thinks in Business Tasks.

The Compiler thinks in Workflow IR.

The Runtime thinks in Execution.

No layer should cross these responsibilities.