# Stage 36 — Intent Understanding Engine

Version: 1.0

Status: Implementation Specification

---

# Purpose

The Intent Understanding Engine transforms natural language into structured business intent.

This is the first cognitive stage of the Planner Runtime.

Its responsibility is not to build workflows.

Its responsibility is to understand **what problem should be solved**.

---

# Philosophy

Humans communicate in language.

Businesses operate using goals.

The Intent Engine bridges these two worlds.

```
Natural Language

↓

Business Intent

↓

Business Goals

↓

Planning
```

Planning never consumes raw prompts.

---

# Core Principle

The engine should answer

```
What does the user actually want?

—not—

What words did they type?
```

Understanding intent is semantic.

Not syntactic.

---

# Responsibilities

The Intent Engine owns

✓ Intent detection

✓ Entity extraction

✓ Goal identification

✓ Ambiguity detection

✓ Constraint discovery

✓ Clarification generation

✓ Confidence estimation

Nothing else.

---

# Pipeline

```
User Request

↓

Normalization

↓

Language Detection

↓

Entity Extraction

↓

Intent Detection

↓

Goal Extraction

↓

Constraint Extraction

↓

Confidence Calculation

↓

Clarification (if needed)

↓

Business Intent
```

---

# Inputs

Planner receives

```
Prompt

Planning Context

Conversation

Business Context

Policies

Memory

Capabilities
```

Intent is context-aware.

---

# Outputs

Produces

```python
BusinessIntent

primary_intent

secondary_intents

entities

constraints

goals

confidence

clarification_required

metadata
```

Planner consumes only this object.

---

# Intent Categories

Planner understands

```
Customer Support

Sales

Billing

Orders

Inventory

Analytics

Automation

Knowledge

Security

Administration

General Business
```

Extensible.

---

# Intent Object

```python
BusinessIntent

id

name

description

confidence

priority

source

reasoning_summary
```

Example

```
Refund Request

Confidence

0.97
```

---

# Entity Extraction

Extracts structured entities.

Example

User

```
Refund Sarah's damaged order #1942.
```

Produces

```
Customer

Sarah

Order

1942

Issue

Damaged

Requested Action

Refund
```

---

# Supported Entity Types

```
Customer

Order

Ticket

Invoice

Subscription

Product

Conversation

Policy

Team

Agent

Workflow

Capability

Document

Money

Date

Location
```

Expandable.

---

# Goal Extraction

Intent

```
Refund
```

Goal

```
Refund Completed

Customer Notified

Audit Recorded
```

Goals become planner inputs.

---

# Constraint Extraction

Extract

```
Urgent

Today

Under $100

No Human Approval

Only EU Orders

Use Shopify
```

Constraints affect planning.

---

# Preference Extraction

Planner also identifies preferences.

Example

```
Fastest

Cheapest

Highest Quality

Safest

Lowest Token Cost
```

Preferences influence ranking.

---

# Ambiguity Detection

Planner identifies uncertainty.

Example

```
Refund my order.
```

Questions

```
Which order?

Partial refund?

Full refund?

Store credit?
```

Ambiguity score increases.

---

# Clarification Strategy

Planner only asks questions when required.

Example

```
Missing Order

↓

Ask

↓

Resume Planning
```

Avoid unnecessary interruptions.

---

# Confidence Model

Every intent receives

```
Intent Confidence

Entity Confidence

Goal Confidence

Overall Confidence
```

Separate scores.

---

# Confidence Thresholds

```
0.95+

Automatic

0.80+

Continue

0.60+

Ask if necessary

<0.60

Clarification Required
```

Configurable.

---

# Multi-Intent Requests

Planner supports multiple intents.

Example

```
Refund Sarah

Update Address

Notify Customer
```

Produces

```
Intent Graph
```

Not a single intent.

---

# Intent Graph

```
Refund

↓

Notify

Address Update
```

Later becomes Business Task Graph.

---

# Intent Normalization

Different wording

Same intent.

Example

```
Give money back

Issue refund

Reverse payment

Return payment
```

↓

```
Refund
```

Canonical representation.

---

# Domain Awareness

Intent interpretation depends on domain.

Example

```
Close Ticket
```

Customer Service

↓

Resolve Conversation

---

Project Management

↓

Archive Task

Context determines meaning.

---

# Memory Integration

Intent engine queries

```
Previous Similar Requests

Customer History

Business Lessons

Planner Recommendations
```

Understanding improves.

---

# Capability Awareness

Intent engine knows

```
Available Capabilities
```

It does not select them.

It only knows what kinds of actions are possible.

---

# Intent Explanation

Produces human-readable reasoning.

Example

```
Primary Intent

Refund

Reason

Customer requested reimbursement for damaged order.
```

Useful for debugging.

---

# Failure States

Intent Engine failures

```
Unknown Intent

Ambiguous Intent

Missing Context

Low Confidence

Conflicting Goals
```

Structured failures only.

---

# Intent Events

Emits

```
IntentStarted

EntitiesExtracted

IntentDetected

GoalsExtracted

ConstraintsExtracted

ClarificationGenerated

IntentCompleted
```

Everything observable.

---

# APIs

```python
detect_intent()

extract_entities()

extract_goals()

extract_constraints()

calculate_confidence()

generate_clarification()

normalize_intent()
```

Planner uses

```
understand_request()
```

---

# Suggested Backend Structure

```
app/planner/intent/

    engine.py

    detector.py

    entities.py

    goals.py

    constraints.py

    normalization.py

    confidence.py

    clarification.py

    events.py

    models.py
```

---

# Existing Tajeran Mapping

Already Exists

★★★★★ Conversation Models

★★★★★ Customer Models

★★★★★ Knowledge System

★★★★☆ Agent Runtime

Needs Implementation

☆☆☆☆☆

Intent Engine

☆☆☆☆☆

Entity Extractor

☆☆☆☆☆

Goal Extractor

☆☆☆☆☆

Clarification Engine

☆☆☆☆☆

Intent Confidence

---

# Engineering Principle

Intent Understanding should never generate workflows.

It should only answer one question:

```
What business problem should be solved?
```

Everything after that belongs to the Planner.

---

# Long-Term Vision

Eventually every product built on TCOS shares the same Intent Engine.

Customer Service

Sales

Security

ERP

Developer Platform

HR

Finance

All begin with

```
Understand Business Intent
```

The Planner then decides how to achieve it.

---

# Next Stage

## Stage 37 — Goal Decomposition Engine

The Planner now understands the user's intent.

The next responsibility is transforming high-level business goals into atomic business tasks.

The Goal Decomposition Engine will:

- identify primary and secondary goals,
- recursively decompose goals,
- build the Business Task Graph,
- detect dependencies,
- identify parallel work,
- estimate complexity,
- prepare the graph for capability matching.

This is where planning truly begins.