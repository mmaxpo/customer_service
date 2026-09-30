# Stage 27 — Planning Algorithms

Version: 0.1

Status: Cognitive Core

---

# Purpose

The Planner Engine is responsible for deciding **how to solve a business goal**.

It should not rely on a single LLM prompt.

Instead, it combines deterministic planning algorithms with LLM reasoning only when necessary.

The planner is therefore an algorithmic system with AI augmentation—not an LLM wrapper.

---

# Core Philosophy

Never ask the LLM:

> "Figure everything out."

Instead:

```
Problem

↓

Algorithms

↓

Small Decisions

↓

LLM only where reasoning is required
```

LLMs become one planning component.

Not the planner itself.

---

# Planning Pipeline

```
Goal

↓

Intent Analysis

↓

Goal Decomposition

↓

Constraint Solving

↓

Capability Search

↓

Plan Generation

↓

Plan Ranking

↓

Optimization

↓

Verification Planning

↓

Compilation
```

Each stage is deterministic.

---

# Planner Strategy

The planner never generates one plan.

It generates several candidate plans.

```
Goal

↓

Plan A

Plan B

Plan C

↓

Ranking

↓

Best Plan
```

Planning is search.

Not prediction.

---

# Algorithm 1

Intent Classification

Purpose

Understand the user's real objective.

Example

```
Refund Sarah's order
```

Produces

```
Intent

Refund
```

Preferred implementation

```
Rules

↓

Embedding similarity

↓

Small LLM

↓

Reasoning model
```

Escalation only when confidence decreases.

---

# Algorithm 2

Goal Extraction

Intent answers

"What?"

Goal answers

"When are we finished?"

Example

```
Refund Completed

Customer Notified

Audit Logged
```

Success conditions become explicit.

---

# Algorithm 3

Goal Decomposition

Large goals become smaller goals.

Example

```
Handle Refund Request

↓

Read Order

↓

Validate Policy

↓

Refund

↓

Notify
```

This is hierarchical planning.

---

# Algorithm 4

Task Expansion

Planner expands goals into business tasks.

Goal

```
Resolve Ticket
```

May become

```
Read Conversation

↓

Identify Intent

↓

Search Knowledge

↓

Draft Reply
```

Business only.

---

# Algorithm 5

Dependency Analysis

Tasks depend on each other.

Example

```
Refund

depends on

Read Order
```

Produces a DAG.

No cycles allowed.

---

# Algorithm 6

Constraint Satisfaction

Planner validates

```
Budget

Latency

Permissions

Compliance

Human Approval

Business Policies
```

Before execution begins.

---

# Algorithm 7

Capability Search

Planner searches registry.

Need

```
Refund
```

Finds

```
Refund Capability
```

No prompting.

No guessing.

---

# Algorithm 8

Capability Matching

Multiple capabilities may satisfy one task.

Planner ranks them using

```
Reliability

Latency

Cost

Verification Score

Learning Score
```

Highest score wins.

---

# Algorithm 9

Execution Strategy Selection

One capability

Many implementations.

Example

```
Search Knowledge

↓

Hybrid Search

↓

Vector Search

↓

Graph Search
```

Planner chooses dynamically.

---

# Algorithm 10

Alternative Plan Generation

Planner intentionally creates multiple approaches.

Example

```
Plan A

Search knowledge first

Plan B

Read CRM first

Plan C

Ask customer
```

All valid.

Ranking decides.

---

# Algorithm 11

Plan Ranking

Every candidate receives a score.

```
Quality

Cost

Latency

Risk

Confidence

Business Value
```

Overall score

```
0.94

↓

Execute
```

---

# Algorithm 12

Cost Optimization

Planner minimizes

```
Money

↓

Tokens

↓

LLM Calls

↓

API Calls

↓

Execution Time
```

Without reducing quality.

---

# Algorithm 13

Parallelization

Planner identifies independent tasks.

Example

```
Read Customer

Read Order

Search Knowledge
```

Compiler later executes them simultaneously.

---

# Algorithm 14

Verification Planning

Planner defines

```
How do we know success?
```

Before execution.

Example

```
Refund Exists

Customer Notified

Audit Created
```

---

# Algorithm 15

Risk Analysis

Planner predicts

```
Failure Probability

↓

Repair Cost

↓

Human Approval Need
```

Before execution starts.

---

# Algorithm 16

Confidence Estimation

Planner estimates

```
Confidence

0.97

↓

Autonomous

0.51

↓

Human Review
```

Confidence affects autonomy.

---

# Algorithm 17

Repair Planning

Planner prepares backup plans.

Example

```
Refund API fails

↓

Retry

↓

Different Provider

↓

Human Approval

↓

Escalate
```

Repair exists before failures happen.

---

# Algorithm 18

Learning Feedback

After execution

Planner records

```
Succeeded?

Cost?

Verification?

Repair Needed?

Customer Satisfaction?
```

Future planning improves.

---

# Candidate Plan Structure

```python
CandidatePlan

goal

task_graph

capability_graph

estimated_cost

estimated_latency

confidence

verification_plan

score
```

Planner usually evaluates several CandidatePlans.

---

# Plan Ranking Formula

Conceptually

```
Score =

Quality

+

Confidence

+

Verification

-

Risk

-

Latency

-

Cost
```

Weights are configurable.

---

# Algorithm Selection Matrix

| Problem | Preferred Technique |
|----------|---------------------|
| Intent | Rules → Embeddings → Small LLM |
| Classification | Small LLM |
| Business reasoning | GPT-5 |
| Variable mapping | Deterministic |
| Dependency graph | Deterministic |
| Cost estimation | Deterministic |
| Capability matching | Registry search |
| Ranking | Weighted scoring |
| Verification | Rules |
| Repair | Planner |

LLMs are used sparingly.

---

# Planning Budget

Planner receives

```python
PlanningBudget

max_llm_calls

max_planning_seconds

max_token_cost

max_candidate_plans
```

Planning itself has limits.

---

# Planner Complexity Levels

Small request

```
Reply Customer

↓

Fast planning
```

Large request

```
Automate Returns Department

↓

Deep planning
```

Planner scales effort.

---

# Deterministic First

Always prefer

```
Rules

↓

Registry

↓

Algorithms

↓

LLM
```

Not

```
LLM

↓

Hope
```

This dramatically improves reliability.

---

# Planner Events

Every planning algorithm emits events.

```
IntentExtracted

GoalExpanded

TasksGenerated

CapabilitiesMatched

PlansRanked

PlanSelected
```

Everything is observable.

---

# Testing

Every algorithm is independently testable.

Input

```
Refund Sarah
```

Expected

```
Intent

↓

Tasks

↓

Capabilities

↓

Best Plan
```

No runtime needed.

---

# Suggested Package

```
app/planner/algorithms/

    intent.py

    decomposition.py

    dependency.py

    constraints.py

    capabilities.py

    ranking.py

    optimization.py

    verification.py

    repair.py

    learning.py
```

---

# Current Tajeran Mapping

Already Exists

★★★★★ Runtime DAG

★★★★★ Execution Engine

★★★★★ Tool System

★★★★★ Node Registry

Needs Implementation

☆☆☆☆☆ Planner Algorithms

☆☆☆☆☆ Candidate Plan Ranking

☆☆☆☆☆ Cost Optimizer

☆☆☆☆☆ Constraint Solver

☆☆☆☆☆ Repair Planner

☆☆☆☆☆ Learning Planner

---

# Engineering Readiness

Runtime

★★★★★

Planning Theory

★★★★★

Implementation

☆☆☆☆☆

Importance

★★★★★

---

# The Most Important Principle

The planner should never "guess."

It should **search**, **evaluate**, **compare**, and **choose**.

That transforms Tajeran from an AI assistant into a true planning system capable of building reliable workflows from natural language while remaining deterministic, explainable, and production-ready.

---

# Next Stage

## Stage 28 — Memory Architecture

The planner cannot reason well without memory.

The next document designs the complete memory system:

- Working Memory
- Episodic Memory
- Semantic Memory
- Business Memory
- Execution Memory
- Long-term Learning
- Memory Retrieval
- Memory Compression
- Memory Aging
- Cross-agent Shared Memory

This will become one of the largest and most valuable components of the entire Cognitive OS.