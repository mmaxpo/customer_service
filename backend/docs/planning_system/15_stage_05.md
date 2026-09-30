# Stage 05 — Capability Ontology

Version: 0.1

---

# Purpose

Business Objects describe

"What exists?"

Capability Ontology describes

"What can be done?"

The planner never reasons in terms of nodes.

It reasons in terms of capabilities.

Example

Customer asks

> Refund my damaged order.

Planner does NOT think

```
shopify.get_order

↓

router

↓

agent.custom

↓

response
```

Planner thinks

```
Read Order

↓

Evaluate Refund Eligibility

↓

Request Approval

↓

Issue Refund

↓

Notify Customer
```

Those are capabilities.

---

# Definition

A Capability is

> An atomic business action that produces a meaningful outcome.

Examples

```
Read Order

Create Refund

Generate Reply

Search Knowledge

Assign Ticket

Update Shipping Address

Detect Intent

Summarize Conversation
```

Capabilities are independent from implementation.

---

# Core Rule

One capability

↓

One responsibility

Never

```
Read Order

+

Refund

+

Generate Reply
```

inside one capability.

Instead

```
Read Order

↓

Refund

↓

Generate Reply
```

Planner combines them.

---

# Capability Structure

Every capability has metadata.

```
ID

Name

Description

Category

Inputs

Outputs

Requirements

Permissions

Cost

Latency

Risk

Confidence

Fallback

Implementation
```

---

Example

Capability

```
refund.create
```

Description

```
Creates a refund through the commerce platform.
```

Inputs

```
Order

Amount

Reason
```

Outputs

```
Refund ID

Status
```

Requires

```
Shopify Connection

Approval

Order
```

Risk

```
High
```

---

# Capability Categories

Planner organizes capabilities by category.

---

Customer

```
Read Customer

Update Customer

Create Customer

Search Customer

Merge Customer
```

---

Conversation

```
Read Conversation

Summarize

Detect Intent

Detect Sentiment

Generate Reply

Translate

Classify
```

---

Commerce

```
Read Order

Refund

Cancel

Reship

Update Address

Track Shipment

Read Inventory
```

---

Knowledge

```
Search

Retrieve

Rank

Summarize

Embed

Index

Delete
```

---

Workflow

```
Generate Workflow

Validate Workflow

Repair Workflow

Execute Workflow

Resume Workflow

Cancel Workflow

Replay Workflow
```

---

Agent

```
Plan

Execute

Verify

Repair

Delegate

Call Tool

Pause

Resume
```

---

Platform

```
Run Job

Store Event

Publish Event

Wait

Schedule

Notify
```

---

# Capability Relationships

Some capabilities depend on others.

Example

```
Refund

↓

Requires

↓

Read Order
```

Another

```
Generate Reply

↓

Requires

↓

Conversation

Knowledge

Decision
```

Planner learns dependencies.

---

# Capability Inputs

Every capability explicitly declares inputs.

Example

```
Read Order

Input

Order ID
```

Refund

Input

```
Order

Reason

Amount
```

Reply

Input

```
Conversation

Knowledge

Decision
```

Planner can automatically satisfy missing inputs.

---

# Capability Outputs

Outputs become graph edges.

Example

```
Read Order

↓

Order
```

↓

Refund

↓

Refund Result

↓

Reply

↓

Customer Message
```

Outputs feed later capabilities.

---

# Capability Preconditions

Some capabilities require conditions.

Refund

Requires

```
Order Exists

Paid

Refundable

Permission

Approval
```

Planner checks before execution.

---

# Capability Postconditions

Planner verifies expected state.

Refund

Expected

```
Refund Created

↓

Notification Sent

↓

Conversation Updated
```

If missing

↓

Repair.

---

# Capability Risk Levels

Every capability has a risk score.

---

Low

```
Search Knowledge

Summarize

Translate
```

---

Medium

```
Assign Ticket

Change Priority

Create Draft
```

---

High

```
Refund

Cancel Order

Delete Data

Charge Payment
```

High-risk capabilities require approval.

---

# Capability Cost

Planner estimates

```
Latency

Token Cost

Money

API Calls
```

Example

Knowledge Search

```
Cheap
```

Web Search

```
Expensive
```

GPT-5

```
Higher cost
```

Planner optimizes automatically.

---

# Capability Confidence

Planner estimates

```
How certain am I?
```

Example

Intent Detection

```
96%
```

Policy Match

```
91%
```

Refund Decision

```
84%
```

Low confidence

↓

Verification

↓

Human review.

---

# Capability Permissions

Planner understands

Who may execute?

Example

Refund

```
Requires

Manager Approval
```

Generate Reply

```
AI Allowed
```

Delete Customer

```
Admin Only
```

Planner checks permissions before planning.

---

# Capability Implementations

Capability

```
Read Order
```

may have multiple implementations.

Shopify

↓

Read Order

WooCommerce

↓

Read Order

Magento

↓

Read Order

Planner chooses implementation automatically.

Business capability never changes.

---

# Composite Capabilities

Planner builds larger capabilities.

Example

Handle Refund Request

↓

Read Order

↓

Evaluate Policy

↓

Approval

↓

Refund

↓

Generate Reply

↓

Notify Customer

Planner eventually stores these as reusable recipes.

---

# Capability Discovery

Planner searches

```
Goal

↓

Capabilities

↓

Dependencies

↓

Execution Plan
```

Example

Goal

```
Customer wants replacement.
```

Planner finds

```
Read Order

↓

Inventory

↓

Replacement Eligibility

↓

Approval

↓

Replacement

↓

Reply
```

---

# Capability Registry

Future structure

```
Capability

↓

Metadata

↓

Requirements

↓

Inputs

↓

Outputs

↓

Risk

↓

Implementation

↓

Average Success Rate

↓

Average Cost

↓

Average Latency
```

Planner queries this registry continuously.

---

# Capability Learning

Eventually planner records

```
Used 24,000 times

Average 1.8 sec

98% success

Most common dependency

Read Order
```

Planner improves automatically.

---

# Mapping to Runtime

Planner

↓

Capabilities

↓

Business Graph

↓

Workflow Graph

↓

Runtime DAG

↓

Nodes

↓

Execution

Planner never creates runtime nodes directly.

Nodes are implementation details.

---

# Tajeran Today

Already Exists

★★★★★

Execution Runtime

★★★★★

Node Catalog

★★★★★

Tool Registry

★★★★☆

Agent Runtime

Planner Capability Understanding

★☆☆☆☆

Capability Registry

☆☆☆☆☆

Ontology

☆☆☆☆☆

---

# Target Architecture

Prompt

↓

Intent

↓

Business Objects

↓

Capabilities

↓

Dependency Graph

↓

Workflow

↓

Execution

↓

Verification

↓

Repair

↓

Result

Everything above execution is planner intelligence.

Everything below execution is your runtime.

---

# Why This Stage Matters

Without Capability Ontology

Planner asks

"What node should I use?"

With Capability Ontology

Planner asks

"What business action accomplishes the user's goal?"

That is the difference between a workflow engine and an intelligent orchestration platform.

---

# Next Investigation

Stage 06

Planner Memory Model

The planner must remember what it has already discovered while planning.

It needs working memory, long-term execution memory, capability memory, and decision memory.

Without memory, every planning step starts from zero.

With memory, planning becomes cumulative, efficient, and increasingly intelligent.