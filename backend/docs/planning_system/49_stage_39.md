# Stage 39 — Capability Discovery & Matching Engine

Version: 1.0

Status: Implementation Specification

---

# Purpose

The Capability Discovery & Matching Engine is responsible for discovering, evaluating, and selecting the best capabilities to satisfy every atomic business task.

The Planner never thinks about runtime nodes.

The Planner thinks only about business capabilities.

This engine bridges

```
Business Task

↓

Platform Capability
```

without exposing execution details.

---

# Philosophy

Business Tasks answer

```
What needs to happen?
```

Capabilities answer

```
What can the platform do?
```

Planning succeeds when the best capability is selected for every task.

---

# Core Principle

The planner never searches for

```
shopify.refund

response

agent.custom

router.rules
```

It searches for

```
Refund Order

Notify Customer

Check Policy

Summarize Conversation
```

The Capability Registry handles the mapping.

---

# Responsibilities

The Capability Matching Engine owns

✓ Capability discovery

✓ Capability filtering

✓ Capability ranking

✓ Compatibility analysis

✓ Primary capability selection

✓ Fallback capability selection

✓ Capability graph construction

Nothing else.

---

# Pipeline

```
Business Task Graph

↓

Capability Discovery

↓

Capability Filtering

↓

Compatibility Analysis

↓

Capability Scoring

↓

Candidate Capabilities

↓

Selection

↓

Capability Graph
```

---

# Input

Consumes

```python
BusinessTaskGraph

PlanningContext

CapabilityRegistry

PlanningConstraints

LearningInsights

BusinessPolicies
```

---

# Output

Produces

```python
CapabilityGraph

task_capability_map

primary_capabilities

fallback_capabilities

selection_metadata

matching_metrics
```

---

# Business Task Example

Planner Task

```
Issue Refund
```

Capability Registry returns

```
Refund Order

Issue Store Credit

Replace Product
```

Planner chooses one.

---

# Capability Definition

Capabilities are business abstractions.

Examples

```
Refund Order

Update Shipping Address

Retrieve Customer

Search Knowledge

Generate Reply

Create Ticket

Notify Customer

Classify Intent

Escalate Conversation

Issue Store Credit
```

No runtime details.

---

# Capability Object

```python
Capability

id

name

version

description

domain

inputs

outputs

constraints

supported_entities

verification_profile

metadata
```

Stable API.

---

# Discovery Phase

Planner searches

```
Business Task

↓

Capability Registry

↓

Matching Capabilities
```

Search is deterministic.

---

# Capability Filtering

Remove

```
Disabled

Deprecated

Permission Denied

Wrong Domain

Version Conflict

Constraint Conflict
```

Only valid capabilities remain.

---

# Compatibility Analysis

Each capability evaluated against

```
Task Requirements

Business Context

Policies

Customer

Environment

Permissions

Learning
```

Produces compatibility score.

---

# Compatibility Score

Example

```
Refund Capability

Task Fit

0.98

Customer Fit

1.00

Policy Fit

0.95

Overall

0.98
```

---

# Capability Ranking

Every candidate ranked using

```
Business Fit

Reliability

Latency

Cost

Verification Quality

Repair History

Learning Score

Confidence
```

Weighted scoring.

---

# Reliability Score

Collected automatically.

Example

```
Capability

Refund

Success

99.4%

Repair Rate

0.2%

Verification Success

99.8%
```

Learning updates continuously.

---

# Cost Score

Planner estimates

```
Execution Cost

LLM Cost

API Cost

Business Cost
```

Used during ranking.

---

# Latency Score

Planner estimates

```
Execution Time

Expected Wait

Human Delay

Verification Time
```

Latency-aware planning.

---

# Verification Quality

Capability also evaluated by

```
Evidence Availability

Verification Confidence

Auditability

Observability
```

Planner prefers verifiable capabilities.

---

# Learning Score

Learning Engine provides

```
Historical Success

Repair Frequency

Customer Satisfaction

Business Outcome
```

Planner becomes increasingly intelligent.

---

# Constraint Validation

Capability checked against

```
Budget

Permissions

Compliance

Policies

Geography

Business Rules
```

Invalid capabilities rejected.

---

# Capability Alternatives

Planner stores

```
Primary

Fallback 1

Fallback 2

Fallback 3
```

Repair later consumes them.

---

# Capability Graph

Produces

```
Task

↓

Primary Capability

↓

Alternative Capabilities
```

Entire graph stored.

---

# Example

```
Retrieve Order

↓

Shopify Order Lookup

↓

Fallback

CRM Lookup

↓

Fallback

Manual Search
```

Planner has options.

---

# Capability Dependencies

Capabilities may require

```
Authentication

Customer

Order

Policy

Previous Capability
```

Planner validates compatibility.

---

# Capability Conflicts

Planner detects

```
Mutually Exclusive

Duplicate

Conflicting Outputs

Version Conflict
```

Resolved before execution.

---

# Capability Composition

Some business tasks require multiple capabilities.

Example

```
Resolve Customer

↓

Retrieve Customer

↓

Read Order

↓

Check Policy

↓

Generate Reply
```

Still represented as one business objective.

---

# Capability Confidence

Every selection has confidence.

```python
CapabilityConfidence

business_fit

technical_fit

historical_confidence

overall_confidence
```

Planner uses confidence during ranking.

---

# Capability Metadata

Every selection stores

```
Selection Reason

Alternatives

Ranking

Scores

Version

Registry Source

Timestamp
```

Fully explainable.

---

# Capability Graph Validation

Checks

```
Missing Capabilities

Duplicate Capabilities

Unreachable Capabilities

Version Mismatch

Dependency Errors
```

Before continuing.

---

# Metrics

Collected

```
Capabilities Evaluated

Capabilities Selected

Average Confidence

Average Cost

Average Reliability

Selection Time
```

Learning consumes metrics.

---

# Events

Engine emits

```
CapabilitySearchStarted

CapabilitiesDiscovered

CapabilitiesFiltered

CapabilitiesRanked

CapabilitySelected

CapabilityGraphCreated
```

Observable planning.

---

# APIs

```python
discover()

filter()

rank()

match()

select()

build_capability_graph()

validate()
```

Planner calls

```
match_capabilities()
```

---

# Suggested Backend Structure

```
app/planner/capabilities/

    engine.py

    discovery.py

    filtering.py

    matching.py

    ranking.py

    scoring.py

    graph.py

    validation.py

    metrics.py

    events.py
```

---

# Existing Tajeran Mapping

Already Exists

★★★★★ Runtime Node Catalog

★★★★★ Agent Tool Registry

★★★★★ Runtime Registry

★★★★☆ Node Metadata

Needs Implementation

☆☆☆☆☆

Business Capability Registry

☆☆☆☆☆

Capability Discovery

☆☆☆☆☆

Capability Ranking

☆☆☆☆☆

Capability Graph

☆☆☆☆☆

Capability Learning Scores

---

# Engineering Principle

The Planner never selects runtime nodes.

It selects business capabilities.

The Compiler later determines how those capabilities execute.

Keeping these layers separate allows the execution engine to evolve independently of business reasoning.

---

# Long-Term Vision

Eventually every product built on TCOS shares the same Capability Registry.

Customer Service

↓

Refund Order

Sales

↓

Create Opportunity

Security

↓

Isolate Endpoint

ERP

↓

Create Purchase Order

HR

↓

Schedule Interview

The Planner always reasons using the same business abstraction regardless of domain.

---

# Next Stage

## Stage 40 — Candidate Plan Generation Engine

The Planner now has:

- Business Task Graph
- Dependency Graph
- Capability Graph

The next responsibility is generating multiple complete execution strategies.

Instead of producing a single plan, the Planner will:

- generate multiple candidate plans,
- vary capability combinations,
- explore execution strategies,
- estimate cost and latency,
- compare trade-offs,
- prepare plans for evaluation and ranking.

This is where the Planner begins behaving like a true search engine rather than a single-pass reasoner.