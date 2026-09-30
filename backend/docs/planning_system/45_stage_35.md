# Stage 35 — Planner Context Engine

Version: 1.0

Status: Implementation Specification

---

# Purpose

The Planner Context Engine is responsible for building the complete planning context before any reasoning begins.

The planner should never query dozens of systems while planning.

Instead, the Context Engine constructs one complete, structured Planning Context.

It becomes the planner's perception layer.

---

# Philosophy

Planning quality depends on context quality.

Not prompt quality.

The planner should never ask

> "What information should I use?"

Instead it receives

```
Planning Context
```

already prepared.

---

# Core Principle

The Context Engine determines

```
What is relevant?

↓

What is important?

↓

What is trustworthy?

↓

What fits inside the planning budget?
```

Everything else is ignored.

---

# Responsibilities

The Context Engine owns

✓ Context collection

✓ Context ranking

✓ Context filtering

✓ Context compression

✓ Context enrichment

✓ Context validation

✓ Context caching

Nothing else.

---

# Context Pipeline

```
User Request

↓

Context Request

↓

Context Collectors

↓

Memory Retrieval

↓

Business Retrieval

↓

Knowledge Retrieval

↓

Constraint Retrieval

↓

Ranking

↓

Filtering

↓

Compression

↓

Planning Context
```

Planner receives exactly one object.

---

# Context Sources

The engine may retrieve information from

```
Business Memory

Semantic Memory

Episodic Memory

Learning Memory

Capability Registry

Policies

Runtime State

Customer Data

Conversation

External Systems
```

Each source has its own collector.

---

# Context Collectors

Every source has a dedicated collector.

Example

```
Conversation Collector

Customer Collector

Memory Collector

Policy Collector

Capability Collector

Knowledge Collector

Learning Collector

Environment Collector
```

Collectors are independent.

---

# PlanningContext Object

Produces

```python
PlanningContext

goal

conversation

customer

business

knowledge

memories

policies

constraints

environment

capabilities

preferences

episodes

lessons

metadata
```

Planner never calls collectors directly.

---

# Context Categories

The engine organizes information into categories.

```
Business

Operational

Knowledge

Memory

Customer

Environment

Policies

Capabilities

Learning
```

Structured context is easier to reason about.

---

# Conversation Context

Collects

```
Conversation

Messages

Attachments

Language

Sentiment

Intent

Entities

Timeline
```

Conversation is normalized.

---

# Customer Context

Collects

```
Customer

Orders

Subscriptions

Tickets

Preferences

Risk

Lifetime Value

History
```

Planner reasons about the customer.

---

# Business Context

Collects

```
Products

Inventory

Pricing

Policies

Teams

Departments

Business Rules
```

Provides organizational awareness.

---

# Capability Context

Collects

```
Available Capabilities

Capability Versions

Capability Statistics

Capability Reliability

Capability Constraints
```

Planner knows platform abilities.

---

# Policy Context

Collects

```
Refund Policy

Security Policy

Compliance

Regional Rules

Company Rules
```

Policies become planning constraints.

---

# Semantic Context

Retrieves

```
Knowledge Base

Documentation

FAQs

Playbooks

Manuals
```

Ranked before inclusion.

---

# Episodic Context

Retrieves

```
Similar Executions

Previous Repairs

Previous Plans

Customer History

Business Episodes
```

Experience informs planning.

---

# Learning Context

Retrieves

```
Lessons

Recommendations

Capability Scores

Planner Insights

Repair Statistics
```

Future planning improves.

---

# Environment Context

Collects

```
Current Time

Region

Language

Available Services

Provider Status

Runtime Health

Feature Flags
```

Planner understands its environment.

---

# Constraint Context

Collects

```
Budgets

Deadlines

Permissions

Compliance

Security

Latency Targets

Token Limits
```

Planner never violates constraints unknowingly.

---

# Context Ranking

Every retrieved item receives a score.

Ranking factors

```
Relevance

Recency

Importance

Confidence

Business Value

Similarity

Source Reliability
```

Highest ranked survive.

---

# Context Filtering

Remove

```
Duplicates

Irrelevant Items

Expired Information

Low Confidence

Conflicting Information
```

Planner receives clean context.

---

# Context Compression

Large context becomes summarized.

Example

```
300 Messages

↓

Conversation Summary

↓

Recent Messages

↓

Open Questions

↓

Relevant Facts
```

Planning remains efficient.

---

# Context Budget

Planner cannot receive unlimited context.

Budget

```
Maximum Tokens

Maximum Objects

Maximum Retrieval Time

Maximum Cost
```

Everything fits inside budget.

---

# Context Priority

Priority order

```
Current Goal

↓

Customer

↓

Business

↓

Policies

↓

Capabilities

↓

Episodes

↓

Knowledge

↓

Everything Else
```

Most relevant first.

---

# Context Validation

Before returning

Engine verifies

```
Required Data Present

No Corruption

No Missing Entities

No Invalid References

Version Compatibility
```

Planner receives valid context.

---

# Context Cache

Frequently requested context is cached.

Example

```
Customer

↓

Business Rules

↓

Capabilities
```

Reduces planning latency.

---

# Context Freshness

Every context item has freshness metadata.

```
Fresh

Recent

Stale

Expired
```

Planner prefers fresh information.

---

# Context Metadata

Every item contains

```
Source

Retrieved At

Confidence

Priority

Version

Collector

Checksum
```

Everything traceable.

---

# Context Events

Engine emits

```
ContextRequested

CollectorStarted

CollectorFinished

ContextRanked

ContextFiltered

ContextCompressed

ContextReady
```

Planning becomes observable.

---

# Context APIs

```python
build_context()

refresh_context()

retrieve()

compress()

rank()

validate()

cache()

invalidate()
```

Planner only calls

```
build_context()
```

---

# Suggested Backend Structure

```
app/planner/context/

    engine.py

    builder.py

    collectors/

        conversation.py

        customer.py

        business.py

        policies.py

        capabilities.py

        semantic.py

        episodic.py

        learning.py

        environment.py

    ranking.py

    filtering.py

    compression.py

    validation.py

    cache.py
```

---

# Existing Tajeran Mapping

Already Exists

★★★★★ Knowledge Search

★★★★★ Runtime State

★★★★★ Customer Service Models

★★★★★ Workflow State

★★★★☆ Events

Needs Implementation

☆☆☆☆☆

Context Engine

☆☆☆☆☆

Collectors

☆☆☆☆☆

Ranking

☆☆☆☆☆

Compression

☆☆☆☆☆

Context Cache

---

# Engineering Principle

The Planner should never gather information.

The Context Engine gathers information.

The Planner only thinks.

This separation keeps planning deterministic, testable and reusable.

---

# Long-Term Vision

Eventually the Context Engine becomes the perception system of TCOS.

Applications never manually assemble prompts.

They request

```
Planning Context
```

The Context Engine determines what the planner needs to know.

---

# Next Stage

## Stage 36 — Intent Understanding Engine

The Planner now has complete context.

The next step is transforming a human request into structured business intent.

The Intent Understanding Engine determines:

- what the user actually wants,
- the primary and secondary goals,
- business entities,
- constraints,
- ambiguity,
- confidence,
- clarification needs.

It is the first true reasoning stage of the Planner Runtime.