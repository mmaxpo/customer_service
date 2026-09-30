# Capability Resolver
**Version:** 0.1 (Architecture Draft)

---

# Vision

The Capability Resolver is responsible for transforming a Business Task Graph into executable platform capabilities.

It answers one question:

> **"Given this business task, what capabilities can satisfy it?"**

It does **not** execute anything.

It does **not** plan.

It only maps business work into executable capabilities.

---

# Position in the Planning Pipeline

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

The Capability Resolver is the bridge between business language and technical execution.

---

# Why This Layer Exists

Without a Capability Resolver:

```
Planner

↓

Workflow Nodes
```

The planner becomes tightly coupled to implementation.

Changing a provider requires changing planning.

---

With a Capability Resolver:

```
Planner

↓

Business Task

↓

Capability Resolver

↓

Workflow
```

Planning never changes.

Only capability mappings change.

---

# Core Philosophy

Business Tasks describe **what**.

Capabilities describe **what the platform knows how to do**.

Runtime Nodes describe **how execution happens**.

These three concepts must remain independent.

---

# Example

Business Task

```
Read Order
```

Capability Resolver

↓

Possible capabilities

```
shopify.order.read

woocommerce.order.read

magento.order.read

erp.order.read
```

↓

Selected capability

```
shopify.order.read
```

↓

Workflow Compiler

↓

Runtime Node

```
shopify.get_order
```

---

# Capability Definition

A Capability represents one reusable business ability of the platform.

Examples

```
conversation.read

conversation.update

order.read

order.refund

knowledge.search

knowledge.ingest

shipping.track

customer.notify

ticket.assign

agent.reply.generate

audit.record
```

Capabilities are stable.

Implementations can change.

---

# Capability Categories

## Customer

```
customer.read

customer.update

customer.search
```

---

## Conversation

```
conversation.read

conversation.write

conversation.summarize
```

---

## Order

```
order.read

order.cancel

order.refund

order.update_address
```

---

## Knowledge

```
knowledge.search

knowledge.ingest

knowledge.generate
```

---

## Ticket

```
ticket.create

ticket.assign

ticket.close
```

---

## Messaging

```
message.send

email.send

sms.send

chat.reply
```

---

## Workflow

```
workflow.execute

workflow.pause

workflow.resume

workflow.cancel
```

---

## AI

```
agent.generate

agent.classify

agent.decide

agent.extract

agent.plan
```

---

# Capability Object

Example

```json
{
    "capability_id":"order.read",

    "name":"Read Order",

    "category":"commerce",

    "provider":"shopify",

    "implementation":"shopify.get_order",

    "cost":2,

    "latency":"low",

    "requires_auth":true
}
```

---

# One Business Task

```
Read Order
```

can resolve into

```
Shopify

↓

shopify.order.read

↓

shopify.get_order
```

or

```
WooCommerce

↓

woocommerce.order.read

↓

woocommerce.get_order
```

Planner never changes.

---

# Resolver Responsibilities

The resolver determines

- available capabilities
- tenant integrations
- provider availability
- permissions
- execution cost
- preferred implementation

It never executes anything.

---

# Resolution Inputs

The resolver may use

```
Business Task

+

Tenant Configuration

+

Installed Integrations

+

Available Providers

+

Permissions

+

Policies

+

Runtime Metadata
```

---

# Resolution Output

Example

```json
{
    "business_task":"Read Order",

    "resolved_capability":"shopify.order.read",

    "implementation":"shopify.get_order",

    "confidence":1.0
}
```

---

# Multi-Provider Resolution

Tenant A

```
Shopify
```

↓

```
Read Order

↓

shopify.get_order
```

Tenant B

```
Magento
```

↓

```
Read Order

↓

magento.get_order
```

Same Planner.

Different capability.

---

# AI Capability Resolution

Business Task

```
Generate Customer Reply
```

Possible implementations

```
agent.custom

agent.mcp

agent.langgraph
```

Planner doesn't care.

Resolver chooses.

---

# Cost-Based Resolution

Business Task

```
Summarize Conversation
```

Available capabilities

```
GPT-5

$

Claude

$$

Local LLM

Free
```

Resolver can choose according to

- policy
- latency
- quality
- budget
- customer tier

---

# Capability Discovery

Every capability should publish metadata.

Example

```json
{
    "id":"knowledge.search",

    "inputs":[
        "query"
    ],

    "outputs":[
        "documents"
    ],

    "estimated_latency":"medium",

    "supports_streaming":false,

    "supports_parallel":true
}
```

This allows automatic planning.

---

# Relationship with Runtime Nodes

Capability

```
knowledge.search
```

↓

Workflow Compiler

↓

Runtime Node

```
knowledge.search
```

Sometimes the mapping is one-to-one.

Sometimes

```
Generate Customer Reply
```

↓

```
agent.generate
```

↓

Runtime

```
agent.custom
```

The compiler owns that translation.

---

# Resolver Is Not a Planner

Planner says

```
Need Read Order
```

Resolver says

```
Use Shopify Read Order
```

Planner never decides providers.

---

# Resolver Is Not Runtime

Resolver chooses

```
shopify.get_order
```

Runtime executes

```
shopify.get_order
```

Different responsibilities.

---

# Capability Registry

Eventually every Tajeran capability should register itself.

Example

```
Capability Registry

├── customer.read

├── conversation.read

├── order.read

├── order.refund

├── knowledge.search

├── knowledge.ingest

├── workflow.execute

├── agent.generate

├── audit.record
```

Planner never hardcodes capabilities.

---

# Why This Layer Matters

Without Capability Resolver

```
Planner

↓

Runtime
```

Everything becomes coupled.

With Capability Resolver

```
Planner

↓

Business Tasks

↓

Capabilities

↓

Compiler

↓

Runtime
```

Every layer becomes independently replaceable.

---

# Current Tajeran Assessment

Business Runtime

★★★★★

Capability Registry

★★☆☆☆

Capability Resolver

★☆☆☆☆

This layer barely exists today but your backend already contains many reusable capabilities waiting to be registered.

Examples already present include:

- Workflow Runtime
- Agent Runtime
- Knowledge Search
- Shopify Integration
- Customer Service
- Human Approval
- Wait Events
- Event Bus
- Timeline
- Audit
- Jobs
- Webhooks

The architecture already exists.

It simply needs to become discoverable.

---

# Relationship to Other Documents

01_tajeran_planning_system.md

↓

02_business_task_graph.md

↓

03_capability_resolver.md

↓

04_workflow_ir.md

---

# Long-Term Vision

The Capability Resolver transforms Tajeran from a collection of integrations into a true execution platform.

Business Tasks remain universal.

Capabilities become discoverable.

Providers become interchangeable.

The Planner remains completely independent from implementation details.

This separation is one of the foundations required for an AI-native, multi-product operating system.