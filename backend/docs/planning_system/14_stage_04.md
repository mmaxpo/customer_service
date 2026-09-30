# Stage 04 — Business Object Model

Version: 0.1

---

# Purpose

The planner should never think in terms of runtime nodes.

Instead, it should reason using business objects.

Example

Customer says

> "Refund my damaged order."

The planner should immediately recognize

```
Customer

Conversation

Order

Refund

Policy

Approval

Reply
```

—not

```
shopify.get_order

router

agent.custom

response
```

Runtime nodes are implementation.

Business objects are reasoning.

---

# Why Business Objects Matter

Humans naturally think like this

```
Customer

↓

Order

↓

Refund

↓

Money
```

not

```
Node A

↓

Node B

↓

Node C
```

Therefore the planner must first build an internal business model.

---

# Core Principle

Every workflow manipulates objects.

Not prompts.

Not tools.

Objects.

---

# Universal Business Objects

Every business can be represented using a relatively small vocabulary.

Example

```
Person

Organization

Conversation

Task

Knowledge

Document

Approval

Product

Order

Payment

Shipment

Inventory

Workflow

Agent

Tool

Notification

Policy
```

Everything else extends these.

---

# Tajeran Core Objects

## Customer

Represents

```
Person requesting service.
```

Attributes

```
Customer ID

Name

Email

Phone

Language

Tags

VIP

Risk Score

Purchase History

Orders

Conversations
```

Relationships

```
Customer

↓

Orders

↓

Tickets

↓

Conversations
```

---

## Conversation

Represents

```
Communication history.
```

Contains

```
Messages

Channel

Intent

Sentiment

Summary

AI Metadata

Attachments

Participants
```

Planner uses conversations as primary context.

---

## Message

Contains

```
Sender

Body

Timestamp

Attachments

Metadata
```

Planner rarely reasons on one message.

It reasons on conversation.

---

## Ticket

Represents

```
Business issue.
```

Fields

```
Priority

Status

Owner

Queue

SLA

Category

Resolution
```

Planner decides

```
Open

Assign

Escalate

Close

Merge
```

---

## Order

Represents

```
Commerce purchase.
```

Fields

```
Order ID

Status

Items

Price

Shipping

Refunds

Returns

Fulfillment
```

Planner frequently reasons using Order.

---

## Product

Contains

```
SKU

Inventory

Price

Vendor

Collections

Policies
```

---

## Shipment

Contains

```
Tracking

Carrier

ETA

Status

Address
```

---

## Refund

Represents

```
Financial reversal.
```

Contains

```
Amount

Reason

Status

Approval

Transaction
```

---

## Policy

Planner constantly asks

```
What policies govern this object?
```

Policies include

```
Refund policy

Shipping policy

Return policy

Escalation policy

Security policy

SLA
```

Policies influence planning.

---

## Knowledge

Represents

```
Facts

Articles

Manuals

FAQs

Documentation

Embeddings
```

Planner never modifies Knowledge.

Planner queries Knowledge.

---

## Workflow

Represents

```
Business process.
```

Contains

```
Goal

Steps

Capabilities

Dependencies

Inputs

Outputs
```

Planner may

```
Generate

Modify

Repair

Reuse
```

Workflows.

---

## Agent

Represents

```
Autonomous reasoning unit.
```

Fields

```
Role

Goal

Capabilities

Context

Memory

Tools

Policies
```

Planner creates agents dynamically.

---

## Tool

Represents

```
Concrete action.
```

Example

```
Read Shopify Order

Send Email

Search Knowledge

Issue Refund

Create Ticket

Read CRM

Call API
```

Tools change state.

---

## Approval

Represents

```
Human decision.
```

Contains

```
Approver

Reason

Decision

Comments

Status
```

Planner inserts Approval when risk requires it.

---

## Notification

Represents

```
Message leaving the system.
```

Examples

```
Email

SMS

Slack

Chat

Webhook
```

---

# Object Relationships

```
Customer

↓

Conversation

↓

Ticket

↓

Order

↓

Refund
```

Another

```
Conversation

↓

Knowledge

↓

Decision

↓

Reply
```

Planner reasons over relationships.

---

# Object Ownership

Each object belongs to a domain.

Example

Customer Service

```
Customer

Conversation

Ticket

Reply

Knowledge
```

Commerce

```
Order

Shipment

Refund

Inventory

Payment
```

Platform

```
Workflow

Agent

Tool

Job

Approval
```

Planner knows where to search.

---

# Object Life Cycle

Every object has states.

Example

Ticket

```
Open

↓

Assigned

↓

Waiting

↓

Resolved

↓

Closed
```

Order

```
Created

↓

Paid

↓

Packed

↓

Shipped

↓

Delivered
```

Refund

```
Requested

↓

Approved

↓

Created

↓

Completed
```

Planner reasons about transitions.

---

# Object Permissions

Planner must know

Who may modify an object?

Example

Refund

```
AI

↓

Recommendation only
```

Human

```
Approval
```

Shopify

```
Execution
```

Permission becomes planning input.

---

# Object Dependencies

Refund depends on

```
Order
```

Shipment depends on

```
Order
```

Conversation depends on

```
Customer
```

Reply depends on

```
Conversation

Knowledge
```

Planner automatically infers prerequisites.

---

# Object Transformations

Objects change.

Example

Conversation

↓

Intent

↓

Decision

↓

Reply

Conversation was transformed into

Business Decision.

---

# Object Graph

Planner stores objects as a graph.

```
Customer

↓

Conversation

↓

Order

↓

Shipment

↓

Refund
```

Relationships become searchable.

---

# Object Memory

Planner remembers

```
Current Order

Current Customer

Current Ticket

Current Workflow
```

rather than raw prompts.

---

# Why This Matters

Without Business Objects

Planner receives

```
Refund my order.
```

LLM must infer everything.

With Business Objects

Planner immediately knows

```
Current Customer

↓

Current Order

↓

Refund Object

↓

Policy

↓

Approval

↓

Workflow
```

Reasoning becomes structured.

---

# Mapping to Runtime

Business Objects

↓

Capabilities

↓

Workflow Graph

↓

Runtime Nodes

↓

Execution Engine

Planner never jumps directly from prompt to runtime.

Business understanding always comes first.

---

# Future Object Learning

Eventually planner will automatically discover

```
New object types

↓

Relationships

↓

Usage frequency

↓

Typical workflows

↓

Dependencies
```

The object model grows with the platform.

---

# Current Readiness

Business Objects

★★☆☆☆

Customer Service Objects

★★★★★

Commerce Objects

★★★★☆

Platform Objects

★★★★☆

Planner Understanding

☆☆☆☆☆

This stage defines the vocabulary that every future planner decision will use.

---

# Next Investigation

Stage 05

Capability Ontology

Business Objects describe **what exists**.

Capability Ontology describes **what can be done** to those objects.

Example

Order

↓

Read

Update

Refund

Cancel

Track

Validate

Duplicate

Notify

The planner learns not only nouns, but verbs.

That is how it begins to reason like an experienced operations architect.