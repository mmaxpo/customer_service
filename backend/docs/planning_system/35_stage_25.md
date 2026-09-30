# Stage 25 — Capability Registry

Version: 0.1

Status: Core Planning Architecture

---

# Purpose

The Capability Registry is the planner's knowledge of its own abilities.

Without a Capability Registry, the planner hallucinates.

With a Capability Registry, the planner reasons from facts.

The planner never asks

> "Maybe I can do this."

Instead it asks

> "Which registered capability solves this task best?"

---

# Philosophy

Capabilities are NOT tools.

Capabilities are NOT workflow nodes.

Capabilities are NOT prompts.

Capabilities describe

> "A business ability."

Examples

```
Refund Order

Read Shopify Order

Search Knowledge

Summarize Conversation

Generate Customer Reply

Send Email

Cancel Subscription

Verify Payment

Assign Ticket
```

These exist independently from implementation.

---

# Why This Layer Exists

Business thinks

```
Refund Customer
```

Runtime thinks

```
shopify.action
```

LLM thinks

```
Tool Call
```

Capability Registry bridges them.

```
Business

↓

Capability

↓

Execution
```

---

# Capability Hierarchy

```
Business Goal

↓

Business Task

↓

Capability

↓

Execution Strategy

↓

Runtime Nodes

↓

Tools

↓

Infrastructure
```

Every layer has one responsibility.

---

# Capability Anatomy

Every capability answers

```
What can I do?

When can I do it?

What do I require?

What do I produce?

How expensive is it?

How reliable is it?
```

---

# Capability Object

```python
Capability

id

name

description

category

version

status

inputs

outputs

constraints

execution_strategies

verification_rules

cost_profile

metadata
```

---

# Example

```
Capability

Refund Order
```

Inputs

```
Order

Reason
```

Outputs

```
Refund Result
```

Requires

```
Shopify Connected

Policy Passed
```

Verification

```
Refund Exists
```

---

# Capability Categories

```
Commerce

Customer Service

Knowledge

Communication

Automation

CRM

Payments

Shipping

Scheduling

Analytics

Security

Developer

Internal
```

Planner filters by category.

---

# Capability Lifecycle

```
Draft

↓

Testing

↓

Production

↓

Deprecated

↓

Removed
```

Planner only uses production capabilities.

---

# Capability Metadata

Every capability contains

```
Owner

Version

Created

Updated

Tenant Scope

Tags

Industry

Language

Risk

Confidence
```

---

# Capability Inputs

Inputs are typed.

Example

```
OrderID

CustomerID

TicketID

Conversation

KnowledgeQuery

RefundReason
```

Never generic strings.

---

# Capability Outputs

Outputs are also typed.

Example

```
Refund

Reply

KnowledgeResult

Order

Shipment

CustomerProfile
```

Planner reasons using outputs.

---

# Preconditions

Example

Refund

Requires

```
Shopify Connected

Refund Eligible

Permission Granted
```

Planner checks before execution.

---

# Postconditions

Example

Refund

Guarantees

```
Refund Created

Audit Logged

Customer Updated
```

Planner uses these during verification.

---

# Side Effects

Capabilities explicitly declare

```
Read Only

Writes Data

Calls External API

Charges Money

Emails Customer

Deletes Data
```

Planner becomes safe.

---

# Human Requirements

Some capabilities require humans.

Example

```
Refund Above $500

↓

Approval Required
```

Planner inserts approval automatically.

---

# Capability Cost

Planner knows cost before execution.

Example

```
Money

$0.02

Tokens

900

Latency

2 seconds

Risk

Low
```

---

# Reliability

Planner stores statistics.

```
Success Rate

97%

Failure Rate

3%

Average Repair

0.2
```

Planner prefers reliable capabilities.

---

# Multiple Implementations

One capability can have many implementations.

Example

Capability

```
Search Knowledge
```

Implementations

```
Vector Search

Hybrid Search

Elastic

OpenSearch

Graph Search
```

Planner chooses.

---

# Capability Providers

Example

Capability

```
Send Email
```

Providers

```
Resend

SES

SendGrid

SMTP
```

Business logic never changes.

---

# Capability Strategies

Example

Refund

Strategy A

```
Shopify API
```

Strategy B

```
ERP Integration
```

Strategy C

```
Human Agent
```

Planner selects dynamically.

---

# Capability Composition

Capabilities compose into workflows.

```
Read Order

↓

Validate Policy

↓

Refund

↓

Notify
```

Planner builds graphs.

---

# Capability Discovery

Planner searches registry.

```
Need

Refund

↓

Registry

↓

Matching Capabilities
```

No LLM guessing.

---

# Semantic Search

Planner can search capabilities.

Example

Prompt

```
Return customer's money
```

Registry finds

```
Refund Order
```

Even wording differs.

---

# Capability Ranking

Planner ranks by

```
Quality

Reliability

Cost

Latency

Risk

Business Preference
```

Best capability wins.

---

# Capability Constraints

Example

```
Requires

Shopify

Region

US

Permission

Billing
```

Planner filters.

---

# Capability Compatibility

Outputs from one capability become inputs to another.

```
Read Order

↓

Order

↓

Refund
```

Automatic chaining.

---

# Capability Graph

Planner creates

```
Capability Graph
```

Not workflow graph.

Example

```
Read Order

↓

Policy Check

↓

Refund

↓

Notify
```

Compiler later converts this.

---

# Capability Registry APIs

```python
find()

search()

validate()

rank()

compose()

resolve()
```

Planner only uses these APIs.

---

# Suggested Backend Structure

```
app/planner/capabilities/

    registry.py

    models.py

    ranking.py

    matcher.py

    search.py

    resolver.py

    statistics.py

    providers.py
```

---

# Integration With Existing Runtime

Today

```
Planner

↓

agent.custom
```

Future

```
Planner

↓

Refund Capability

↓

Compiler

↓

shopify.action

↓

Runtime
```

Cleaner architecture.

---

# Relationship To Nodes

Node

```
shopify.action
```

implements

Capability

```
Refund Order
```

One capability

may compile

to many nodes.

---

# Relationship To Tools

Tool

```
shopify.refund()
```

is NOT a capability.

Capability

```
Refund Customer
```

may use

```
shopify.refund()

audit.write()

notify.customer()
```

Many tools.

One business ability.

---

# Versioning

Capabilities evolve.

```
Refund

v1

↓

Refund

v2

↓

Refund

v3
```

Planner chooses compatible version.

---

# Learning Integration

Learning updates

```
Reliability

Latency

Repair Rate

Verification Score
```

Capability ranking improves automatically.

---

# Testing

Capabilities are independently testable.

```
Input

↓

Expected Output

↓

Verification

↓

Metrics
```

No planner required.

---

# Current Tajeran Mapping

Already Exists

★★★★★ Runtime Nodes

★★★★★ Tool Registry

★★★★★ Shopify Services

★★★★★ Knowledge Services

★★★★☆ Agent Runtime

Missing

☆☆☆☆☆ Capability Registry

☆☆☆☆☆ Capability Ranking

☆☆☆☆☆ Capability Discovery

☆☆☆☆☆ Capability Statistics

☆☆☆☆☆ Capability Composition

---

# Example Registry

```
Customer Service

├── Read Conversation

├── Search Knowledge

├── Classify Intent

├── Generate Reply

├── Escalate Ticket

├── Refund Order

├── Replace Item

├── Track Shipment

├── Close Ticket

└── Collect Feedback
```

Every future product simply contributes more capabilities.

---

# Why This Changes Tajeran

Today your runtime knows

```
How
```

to execute.

After this layer, your planner knows

```
What
```

the platform is capable of doing.

That distinction is what allows prompt-to-workflow generation without hallucinating runtime nodes.

---

# Engineering Readiness

Runtime

★★★★★

Nodes

★★★★★

Tools

★★★★★

Planner

★★☆☆☆

Capability Registry

☆☆☆☆☆

Architectural Importance

★★★★★

---

# Next Stage

## Stage 26 — Workflow Compiler

The Workflow Compiler transforms

```
Business Task Graph

↓

Capability Graph

↓

Business IR

↓

Execution IR

↓

Runtime Workflow
```

This stage is where your existing runtime becomes the execution backend for an autonomous planner.

It will define optimization, graph rewriting, node selection, approval insertion, variable wiring, retries, verification hooks, and compilation passes—very much like a modern programming language compiler.