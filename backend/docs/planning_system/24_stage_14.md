# Stage 14 — Capability Resolver

Version: 0.1

---

# Purpose

The Capability Resolver is one of the most important systems in Tajeran.

Its responsibility is to translate **business intent** into **concrete executable capabilities**.

The planner should never know about Shopify, OpenAI, Stripe, PostgreSQL, Redis, or any implementation detail.

The planner only understands business capabilities.

```
Planner

↓

Capability Resolver

↓

Runtime Nodes
```

---

# Why This Exists

Imagine the planner receives

```
Issue a refund
```

The planner should never think

```
shopify.refund_order
```

because tomorrow the merchant might use

- WooCommerce
- BigCommerce
- Magento
- Stripe
- ERP
- Custom backend

The planner must stay stable forever.

Only the resolver changes.

---

# Philosophy

Planner asks

> What business capability do I need?

Resolver answers

> Which implementation provides it?

---

# Business Capability

A capability is **not a tool**.

A capability is a business operation.

Examples

```
Read Customer

Read Order

Create Refund

Cancel Order

Search Knowledge

Generate Reply

Send Email

Read Inventory

Create Ticket

Assign Agent

Translate Text

Analyze Sentiment

Summarize Conversation
```

Notice

No provider names.

---

# Provider Implementations

One capability can have many implementations.

```
Capability

↓

Read Order
```

Implementations

```
Shopify

WooCommerce

Magento

ERP

Mock

Test Provider
```

Planner never knows.

---

# Resolver Pipeline

```
Capability Request

↓

Tenant Context

↓

Available Providers

↓

Capability Resolver

↓

Resolved Runtime Node
```

---

# Example

Planner asks

```
commerce.order.read
```

Tenant

```
Shopify
```

Resolver returns

```
shopify.get_order
```

---

Different tenant

```
WooCommerce
```

returns

```
woocommerce.get_order
```

Same planner.

Different runtime.

---

# Capability Identifier

Every capability should have a stable id.

Example

```
commerce.order.read

commerce.order.cancel

commerce.refund.create

crm.customer.read

knowledge.search

communication.reply.generate
```

These identifiers never change.

---

# Runtime Mapping

Capability

```
commerce.order.read
```

↓

Runtime

```
shopify.get_order
```

↓

Runtime Node

```
ShopifyGetOrderNode
```

---

# Resolver Inputs

The resolver receives

```python
ResolveRequest(

    capability="commerce.order.read",

    tenant=...,

    permissions=...,

    context=...,

)
```

---

# Resolver Output

```python
ResolvedCapability(

    runtime_node="shopify.get_order",

    provider="shopify",

    confidence=1.0,

    estimated_cost=0,

    estimated_latency=0.2
)
```

---

# Why Confidence Exists

Sometimes multiple providers exist.

Example

```
Search Knowledge
```

Could use

```
Vector Search

Hybrid Search

Web Search

Enterprise Search
```

Resolver scores them.

---

# Provider Registry

Resolver does not hardcode providers.

Instead

```
Capability Registry

↓

Provider Registry

↓

Resolver
```

---

# Capability Registry Example

```yaml
commerce.order.read:

    providers:

        - shopify

        - woocommerce

        - magento
```

---

# Provider Metadata

Each provider exposes metadata.

Example

```yaml
provider:

    shopify

supports:

    refunds

    orders

    inventory

priority:

    100

latency:

    150ms

cost:

    0
```

Planner never sees this.

---

# Selection Rules

Resolver evaluates

Provider installed?

Provider authenticated?

Capability supported?

Merchant permissions?

Policy restrictions?

Availability?

Health?

Cost?

Latency?

Version?

---

# Example

Merchant

```
Shopify Installed

Stripe Installed
```

Planner asks

```
Refund Order
```

Resolver chooses

```
Shopify Refund

NOT Stripe Refund
```

because business object is order.

---

# Fallback

If preferred provider fails

Resolver can return

```
Fallback Provider
```

Example

```
Knowledge Search

↓

Enterprise Search

↓

Fallback

↓

Web Search
```

---

# Multi-provider Composition

Some capabilities require multiple providers.

Example

```
Read Order
```

↓

Shopify

```
Read Customer
```

↓

CRM

↓

Combine

↓

Planner receives unified object.

---

# Capability Versioning

Capabilities evolve.

```
commerce.order.read

v1

v2
```

Resolver manages versions.

Planner remains unchanged.

---

# Capability Discovery

Resolver can answer

```
What capabilities exist?
```

Planner can dynamically discover new capabilities.

Example

```
Merchant installs Zendesk

↓

Resolver exposes

ticket.read

ticket.reply

ticket.assign
```

Planner immediately gains new abilities.

No retraining.

---

# Runtime Independence

Today

```
shopify.get_order
```

Tomorrow

```
shopify.graphql.order.read
```

Planner remains identical.

---

# Testing

Resolver tests are deterministic.

Input

```
commerce.order.read
```

↓

Expected

```
shopify.get_order
```

Every capability should have golden tests.

---

# Current Tajeran Mapping

Already Exists

✅ Runtime Node Registry

✅ Node Types

✅ Shopify Nodes

✅ Knowledge Nodes

✅ Customer Chat Nodes

✅ Agent Nodes

Missing

❌ Capability Registry

❌ Resolver

❌ Provider Metadata

❌ Provider Ranking

❌ Capability Discovery

---

# Suggested Backend Structure

```
app/planner/capabilities/

    registry.py

    resolver.py

    providers.py

    ranking.py

    discovery.py

    models.py
```

---

# Registry Example

```python
registry.register(

    capability="commerce.order.read",

    provider="shopify",

    runtime_node="shopify.get_order",

    priority=100,
)
```

---

# Future Expansion

Eventually capabilities become installable.

Example

Merchant installs

```
Salesforce
```

Immediately resolver adds

```
crm.customer.read

crm.customer.update

crm.case.create
```

Planner automatically discovers them.

---

# Why This Is Foundational

The Capability Resolver is what separates Tajeran from a workflow editor.

Instead of building workflows around nodes, Tajeran builds workflows around **business meaning**.

That allows:

- provider independence
- multi-platform support
- tenant customization
- runtime evolution
- dynamic capability discovery
- AI planning that reasons in business language instead of implementation details

---

# MVP

Version 1 only needs:

- Static capability registry
- One provider per capability
- Direct runtime mapping
- Deterministic resolution
- Golden tests

No ranking or fallback yet.

---

# Long-Term Vision

```
User Prompt

↓

Planner

↓

Business Capabilities

↓

Capability Resolver

↓

Workflow Compiler

↓

Runtime DAG

↓

Execution
```

The planner never knows how the work is done.

It only knows **what business capability is required**.

---

# Current Readiness

Runtime Nodes

★★★★★

Runtime Registry

★★★★★

Business Capability Model

★★☆☆☆

Capability Resolver

☆☆☆☆☆

Dynamic Capability Discovery

☆☆☆☆☆

---

# Next Investigation

## Stage 15 — Workflow Generator

This is where Tajeran first becomes truly generative.

Instead of a human dragging nodes onto a canvas, the planner will generate an entire business workflow from a natural-language request using the Planning Graph, Capability Graph, and Workflow IR you've defined in the previous stages.