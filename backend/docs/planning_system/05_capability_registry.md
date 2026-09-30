# Capability Registry
**Version:** 0.1 (Architecture Draft)

---

# Vision

The Capability Registry is the knowledge base of everything Tajeran knows how to do.

It is the bridge between planning and execution.

```
Planner

↓

Capability Registry

↓

Workflow Compiler

↓

Runtime
```

The planner never invents capabilities.

It discovers them.

---

# Why It Exists

Imagine the user says

```
Refund this order.
```

The planner should not directly produce

```
shopify.refund
```

Instead it asks

```
Which capability performs refunds?
```

The registry answers

```
shopify.refund
```

---

Without a registry

Planner guesses.

With a registry

Planner discovers.

---

# Capability

A capability is one business action the platform can perform.

Examples

```
knowledge.search

shopify.order.read

shopify.refund

customer.reply.generate

ticket.create

workflow.run

agent.run

human.approval

email.send

conversation.read

customer.lookup
```

Notice

Capabilities describe business abilities.

Not Python classes.

Not runtime nodes.

---

# Capability Registry Responsibilities

The registry must answer

```
What can Tajeran do?

How is it executed?

What inputs does it need?

What outputs does it produce?

When should it be used?

When should it NOT be used?

Does it require approval?

Estimated cost?

Estimated latency?
```

---

# Capability Object

Example

```json
{
    "id":"shopify.refund",

    "name":"Refund Order",

    "category":"commerce",

    "description":"Create a Shopify refund.",

    "inputs":[
        "order",
        "refund_amount"
    ],

    "outputs":[
        "refund_result"
    ],

    "approval":"required",

    "runtime_node":"shopify.action",

    "tool":"shopify_refund"
}
```

---

# Planner View

Planner never sees Python.

Planner only sees

```
Capability

↓

Description

↓

Inputs

↓

Outputs

↓

Policies
```

---

# Runtime View

Runtime does not care about descriptions.

Runtime only needs

```
runtime_node

configuration

execution policy
```

---

# Capability Categories

Example

## Customer Service

```
conversation.read

conversation.search

customer.lookup

ticket.create

ticket.update

reply.generate
```

---

## Commerce

```
order.read

refund.create

cancel.order

shipping.update

reship.order
```

---

## Knowledge

```
knowledge.search

knowledge.retrieve

knowledge.ingest
```

---

## Communication

```
email.send

chat.reply

sms.send

notification.send
```

---

## AI

```
agent.run

classifier.run

planner.run

summarizer.run
```

---

## Workflow

```
workflow.start

workflow.resume

workflow.pause

subworkflow.run
```

---

# Capability Metadata

Every capability should contain metadata.

Example

```json
{
    "latency":"medium",

    "cost":"low",

    "side_effect":true,

    "approval_required":true,

    "parallel_safe":false
}
```

This helps the planner optimize execution.

---

# Inputs

Inputs are logical business objects.

Example

```
Conversation

Customer

Order

Policy

Ticket
```

Never

```
SQL

Redis

JSON

HTTP
```

---

# Outputs

Outputs are business concepts.

```
Refund Result

Shipping Status

Customer Reply

Policy Answer

Risk Score
```

---

# Preconditions

Capabilities may require conditions.

Example

```
Requires

Shopify Connected

Order Exists

Customer Authenticated
```

Planner uses these before selecting capabilities.

---

# Side Effects

Some capabilities modify the world.

Example

```
Refund

Cancel Order

Send Email

Create Ticket
```

Some do not.

```
Knowledge Search

Summarization

Classification

Intent Detection
```

Planner should know the difference.

---

# Capability Cost

Planner should know approximate cost.

Example

```
Knowledge Search

Low

--------

GPT-5

Medium

--------

Deep Research

High
```

Planner can optimize workflows automatically.

---

# Capability Latency

Example

```
Knowledge Search

100ms

--------

LLM

3 seconds

--------

Shopify Refund

1 second

--------

Deep Research

2 minutes
```

---

# Approval Rules

Capabilities may require approval.

```
Refund

YES

--------

Cancel Order

YES

--------

Search Knowledge

NO
```

Planner should not guess.

Registry tells it.

---

# Capability Discovery

Planner asks

```
Need:

Refund customer

↓

Registry Search

↓

shopify.refund

↓

Compiler
```

---

# Capability Composition

Complex tasks use multiple capabilities.

Example

```
Read Conversation

↓

Read Order

↓

Search Policy

↓

Generate Decision

↓

Generate Reply
```

Planner builds this automatically.

---

# Capability Search

Registry should support semantic search.

Example

Planner asks

```
Customer wants money back.
```

Registry returns

```
Refund Order

Return Policy

Customer Reply

Order Read
```

Not keyword matching.

Meaning matching.

---

# Registry Implementation

The registry should not be hardcoded forever.

Eventually

```
Capability YAML

↓

Registry Loader

↓

Memory

↓

Planner
```

or

```
Python Decorators

↓

Registry Builder

↓

Planner
```

---

# Future Auto Registration

Example

```python
@capability(
    id="knowledge.search",
    category="knowledge",
    cost="low",
    latency="fast",
)
class KnowledgeSearchNode:
    ...
```

Registry builds itself automatically.

---

# Current Tajeran Mapping

Today many capabilities already exist.

Examples

```
Knowledge Search

Shopify Get Order

Shopify Refund

Shopify Cancel

Customer Chat

Workflow Runtime

Human Approval

Wait Time

Wait Event

Platform Jobs

Subworkflow

Agent Runtime

LLM Generate

Response Node
```

Most of the work is documenting them.

Not rewriting them.

---

# Planner Interaction

Planner never asks

```
Execute refund.
```

Planner asks

```
Which capability satisfies

"Customer wants refund."
```

Registry answers

```
shopify.refund
```

Planner then constructs a Business Task Graph.

---

# Runtime Interaction

Compiler maps

```
Capability

↓

Runtime Node

↓

Configuration

↓

Execution
```

The Runtime never searches the registry.

Planning is already complete.

---

# Benefits

## No Hallucinated Tools

Planner only uses registered capabilities.

---

## Lower Token Usage

Planner receives structured capability summaries.

Not source code.

---

## Better Explainability

Planner can explain

```
I selected Refund because:

• Customer requested refund

• Shopify connected

• Approval required

• Policy allows refund
```

---

## Better Optimization

Planner can choose

```
Fastest

Cheapest

Most Reliable

Highest Quality
```

depending on the objective.

---

# Current Tajeran Assessment

Capability Inventory

★★★★★

Capability Registry

★☆☆☆☆

Semantic Discovery

☆☆☆☆☆

Automatic Registration

☆☆☆☆☆

The platform already contains a rich set of capabilities. The missing piece is exposing them through a formal registry that planners can query.

---

# Relationship to Other Documents

01_tajeran_planning_system.md

↓

02_business_task_graph.md

↓

03_capability_resolver.md

↓

04_workflow_ir.md

↓

05_capability_registry.md

↓

06_workflow_compiler.md

---

# Long-Term Vision

The Capability Registry becomes Tajeran's internal "operating system API."

Every planner, agent, template, marketplace workflow, and future AI model discovers platform functionality through this registry instead of relying on hardcoded assumptions.

This makes Tajeran extensible, explainable, and resilient as the platform grows from dozens of capabilities to hundreds or thousands.