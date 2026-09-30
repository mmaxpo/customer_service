# Stage 09 — Capability Registry

Version: 0.1

---

# Purpose

The Runtime executes nodes.

The Planner discovers capabilities.

Those are not the same thing.

Example

Runtime knows

```
shopify.get_order
```

Planner knows

```
Read Order
```

Planner should never care whether

Read Order is implemented using

```
Shopify

WooCommerce

Magento

REST API

Internal Database
```

That is implementation.

The planner reasons only about business capabilities.

---

# Philosophy

Capabilities become the vocabulary of Tajeran.

Instead of asking

```
Which node should I execute?
```

Planner asks

```
Which business capability satisfies this goal?
```

---

# Registry Position

```
User Prompt

↓

Intent

↓

Business Objects

↓

Capability Registry

↓

Planner

↓

Workflow Compiler

↓

Execution Runtime
```

The registry sits between understanding and planning.

---

# Why Runtime Catalog Is Not Enough

Current Runtime Catalog

```
agent.custom

knowledge.search

response

router

join

wait

shopify.get_order
```

These are implementation nodes.

Planner should instead see

```
Read Order

Search Knowledge

Generate Reply

Create Refund

Wait For Approval

Notify Customer
```

Business capabilities.

---

# Registry Responsibilities

Capability Registry answers

```
What can Tajeran do?
```

```
What inputs are required?
```

```
What objects are produced?
```

```
How expensive is it?
```

```
How risky is it?
```

```
Which implementation exists?
```

```
What permissions are needed?
```

```
What alternatives exist?
```

---

# Registry Architecture

```
Capability Registry

│

├── Capability Metadata

├── Business Objects

├── Constraints

├── Dependencies

├── Implementations

├── Statistics

├── Policies

└── Learning Data
```

---

# Capability Definition

Every capability has metadata.

```
Capability ID

Display Name

Description

Category

Version

Status

Owner
```

Example

```
commerce.order.read
```

---

# Business Description

Planner reasons using descriptions.

Example

```
Reads an order from the connected commerce platform.
```

Instead of

```
Calls Shopify REST endpoint.
```

---

# Inputs

Capability explicitly declares

```
Required Inputs

Optional Inputs

Accepted Object Types
```

Example

```
Order ID

or

Conversation

or

Customer
```

Planner can satisfy missing inputs automatically.

---

# Outputs

Outputs become graph edges.

Example

```
Read Order

↓

Order
```

Planner now knows

Refund can consume

Order.

---

# Object Types

Capability declares

Consumes

```
Conversation

Customer
```

Produces

```
Order
```

Planner builds object graph.

---

# Dependencies

Registry stores

```
Requires

↓

Read Customer

↓

Read Order
```

Planner automatically inserts dependencies.

---

# Constraints

Capability declares

```
Approval Required

Manager Role

Business Hours

Region

Store Connected
```

Planner checks before execution.

---

# Risk Metadata

Every capability contains

```
Risk Level

Business Impact

Financial Impact

Security Impact

Compliance Impact
```

Planner inserts

Approval

when necessary.

---

# Cost Metadata

Planner estimates

```
Average Tokens

Average Time

Average API Calls

Average Cost
```

Example

Knowledge Search

```
Cheap
```

GPT-5

```
Expensive
```

Planner optimizes.

---

# Success Statistics

Eventually registry records

```
Average Success

Average Retry

Average Duration

Failure Reasons

Typical Usage
```

Planner becomes data-driven.

---

# Multiple Implementations

One capability

↓

Many implementations.

Example

Capability

```
Read Order
```

Implementations

```
Shopify

WooCommerce

Magento

ERP

CSV

Mock
```

Planner never changes.

Only implementation changes.

---

# Selection Rules

Registry chooses implementation.

Example

```
Commerce Platform

↓

Shopify

↓

Use Shopify Adapter
```

Planner remains platform independent.

---

# Capability Tags

Search becomes semantic.

Example

```
refund

commerce

financial

shopify

customer service
```

Planner searches tags.

---

# Capability Categories

Planner groups capabilities.

Example

Customer

```
Read

Create

Update

Merge

Delete
```

Conversation

```
Summarize

Reply

Translate

Detect Intent
```

Commerce

```
Read Order

Refund

Cancel

Shipment

Inventory
```

Knowledge

```
Search

Retrieve

Rank

Embed
```

Platform

```
Workflow

Approval

Notification

Jobs

Scheduling
```

---

# Capability Policies

Some capabilities require policies.

Refund

↓

Refund Policy

Delete Customer

↓

Security Policy

Planner loads policies automatically.

---

# Capability Alternatives

Registry stores alternatives.

Example

Planner needs

```
Knowledge Search
```

Available

```
Vector Search

Hybrid Search

Web Search

FAQ Cache
```

Planner selects one.

---

# Capability Composition

Registry also stores

Composite Capabilities.

Example

```
Handle Refund Request
```

Expands into

```
Read Order

↓

Evaluate Policy

↓

Approval

↓

Refund

↓

Reply

↓

Notify
```

Planner reuses composites.

---

# Discovery API

Planner asks

```
Goal

↓

Capability Search

↓

Candidate Capabilities

↓

Rank

↓

Select
```

Registry answers.

---

# Ranking Factors

Capabilities ranked by

```
Business Fit

Confidence

Cost

Latency

Availability

Historical Success
```

Planner chooses best.

---

# Registry Learning

Every execution updates registry.

Example

```
Refund

Executed

42,000 times

98.7%

Average

2.3 sec
```

Planner improves naturally.

---

# Current Backend Mapping

Current Runtime already has

```
Node Registry

Node Config

Tool Registry
```

Capability Registry becomes

one abstraction higher.

Planner never sees nodes.

---

# Suggested Folder

```
planner/

    registry/

        capabilities/

        metadata/

        policies/

        implementations/

        ranking/

        search/

        statistics/
```

---

# Planner Interaction

```
Intent

↓

Capability Search

↓

Candidate Capabilities

↓

Dependency Planner

↓

Workflow Compiler
```

Planner never builds workflow from scratch.

It discovers capabilities.

---

# Example

Prompt

```
Customer wants refund.
```

Registry returns

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

Planner builds graph.

Compiler creates runtime workflow.

Execution Runtime executes.

---

# Future Scale

Eventually

```
5,000+

Capabilities

Across

Customer Service

CRM

Finance

HR

Marketing

Operations

Development

Infrastructure
```

Planner still uses one registry.

---

# Current Readiness

Runtime Node Registry

★★★★★

Tool Registry

★★★★★

Execution Catalog

★★★★★

Capability Registry

☆☆☆☆☆

Capability Metadata

☆☆☆☆☆

Capability Search

☆☆☆☆☆

Ranking

☆☆☆☆☆

Statistics

☆☆☆☆☆

---

# Why This Stage Matters

Execution Runtime knows

**How to execute.**

Capability Registry knows

**What the platform is capable of.**

This distinction is what allows Tajeran to evolve from a workflow engine into a general business operating system.

---

# Next Investigation

Stage 10 — Business Object Registry

If Capability Registry answers

"What can Tajeran do?"

Business Object Registry answers

"What exists in the customer's business?"

The planner will combine:

Business Objects

+

Capabilities

↓

Business Graph

↓

Workflow

↓

Execution

This is where true business reasoning begins.