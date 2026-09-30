# 05 — Planner Runtime

**Status:** Implementation Specification

**Subsystem:** TCOS Cognitive Layer

**Owner:** Cognitive Runtime

**Version:** 1.0

---

# 1. Vision

The Planner Runtime is the cognitive engine of the Tajeran Cognitive Operating System.

It is responsible for transforming a business goal into an executable business strategy.

Unlike the Execution Runtime, which executes deterministic workflows, the Planner Runtime executes reasoning workflows.

Its responsibility is to decide

- what should happen,
- why,
- in what order,
- using which capabilities,
- with which confidence,
- under which constraints.

It never executes business logic.

It produces Business IR.

---

# 2. Responsibilities

The Planner Runtime owns

- Planning sessions
- Context collection
- Intent understanding
- Goal decomposition
- Constraint analysis
- Dependency analysis
- Capability matching
- Candidate generation
- Plan evaluation
- Plan selection
- Verification planning
- Planning persistence
- Planning events
- Planning metrics

The Planner Runtime does NOT own

- Runtime execution
- Workflow scheduling
- Runtime state
- Agent execution
- Learning
- Repair
- Verification execution

---

# 3. Architecture

```
User Goal

↓

Planning Session

↓

Context Engine

↓

Intent Engine

↓

Goal Decomposition

↓

Dependency Analysis

↓

Capability Matching

↓

Candidate Generation

↓

Plan Evaluation

↓

Business IR

↓

Workflow Compiler
```

---

# 4. Internal Modules

The Planner Runtime consists of independent services.

```
Planner Runtime

├── Session Manager

├── Context Engine

├── Intent Engine

├── Goal Engine

├── Dependency Engine

├── Capability Engine

├── Candidate Generator

├── Evaluation Engine

├── Planning Memory

├── Planner Cache

├── Event Publisher

└── Metrics
```

Each service owns one responsibility.

---

# 5. Planning State Machine

```
Idle

↓

Collect Context

↓

Understand Intent

↓

Extract Goals

↓

Decompose Goals

↓

Analyze Dependencies

↓

Match Capabilities

↓

Generate Plans

↓

Evaluate Plans

↓

Select Plan

↓

Generate Business IR

↓

Finished
```

Planning is deterministic.

---

# 6. Planning Session

Every request creates

```python
PlanningSession

session_id

tenant_id

user_id

goal

context

state

events

metrics

business_plan

status
```

Planner becomes replayable.

---

# 7. Context Engine

Collects

```
Conversation

Customer

Business

Knowledge

Memory

Capabilities

Policies

Environment

Learning

Constraints
```

Produces

```
PlanningContext
```

Planner never queries services directly.

---

# 8. Intent Engine

Transforms

```
Natural Language

↓

Business Intent
```

Outputs

```
Primary Intent

Entities

Goals

Constraints

Confidence
```

---

# 9. Goal Engine

Converts

```
Business Goal

↓

Atomic Business Tasks
```

Produces

```
Business Task Graph
```

---

# 10. Dependency Engine

Analyzes

```
Dependencies

Parallelism

Critical Path

Resource Conflicts

Constraints
```

Produces optimized planning graph.

---

# 11. Capability Engine

Maps

```
Business Tasks

↓

Business Capabilities
```

Never runtime nodes.

Produces

```
Capability Graph
```

---

# 12. Candidate Generator

Produces multiple complete plans.

Strategies include

- Fastest
- Cheapest
- Safest
- Lowest Risk
- Highest Quality
- Learned Strategy

Never produces only one plan.

---

# 13. Evaluation Engine

Scores every plan.

Evaluation dimensions

```
Business Value

Cost

Latency

Complexity

Reliability

Risk

Verification

Repair Probability

Learning Score
```

Highest ranked plan wins.

---

# 14. Planning Memory

Stores

```
Planning Sessions

Plans

Metrics

Events

Failures

Decisions

Candidate Plans
```

Independent from Runtime memory.

---

# 15. Planning Cache

Caches

- Context
- Capability lookups
- Similar plans
- Business templates
- Compilation results

Reduces planning latency.

---

# 16. Planner Events

Publishes

```
PlanningStarted

ContextCollected

IntentDetected

GoalsCreated

TasksExpanded

CapabilitiesMatched

PlanGenerated

PlanRejected

PlanSelected

BusinessIRCreated

PlanningCompleted
```

Observable planning.

---

# 17. Planner APIs

```
plan()

replan()

resume()

cancel()

compare()

simulate()

explain()

history()

events()
```

Primary API

```
plan(goal)
```

---

# 18. Planning Metrics

Track

```
Planning Duration

Candidate Plans

Capability Searches

LLM Calls

Tokens

Estimated Runtime

Estimated Cost

Confidence

Planning Accuracy
```

Feeds Learning Engine.

---

# 19. Planner Persistence

Store

```
Planning Sessions

Business Plans

Events

Candidate Plans

Metrics

Snapshots

Decisions
```

Supports replay.

---

# 20. Planner Observability

Planner UI visualizes

```
Goal

↓

Intent

↓

Task Graph

↓

Capability Graph

↓

Candidate Plans

↓

Selected Plan

↓

Business IR
```

Every decision explainable.

---

# 21. Planner Security

Enforces

- Tenant isolation
- Capability permissions
- Planning budgets
- Token budgets
- Business policies
- Audit logging

Planner cannot create unauthorized plans.

---

# 22. Performance Targets

Small Goal

```
<300 ms
```

Medium Goal

```
<1 second
```

Complex Goal

```
<5 seconds
```

Planning should feel interactive.

---

# 23. Backend Structure

```
app/planner/

    runtime.py

    session.py

    context/

    intent/

    goals/

    dependency/

    capabilities/

    candidate_generation/

    evaluation/

    persistence/

    cache/

    events/

    metrics/

    models/
```

---

# 24. Existing Tajeran Mapping

Already Exists

★★★★★ Runtime Engine

★★★★★ Agent Runtime

★★★★★ Workflow Persistence

★★★★★ Event Bus

★★★★★ Jobs

★★★★★ Runtime State

★★★★★ Knowledge

★★★★★ Customer Service Models

Needs New Implementation

☆☆☆☆☆

Planner Runtime

☆☆☆☆☆

Planning Sessions

☆☆☆☆☆

Planning Context

☆☆☆☆☆

Capability Matching

☆☆☆☆☆

Candidate Generation

☆☆☆☆☆

Plan Evaluation

Can Reuse

- Runtime events
- Runtime persistence
- Existing integrations
- Existing knowledge system
- Existing workflow catalog
- Existing runtime infrastructure

The Planner should reuse the platform, not duplicate it.

---

# 25. Manual Test Plan

Validate

- Context creation
- Intent detection
- Goal decomposition
- Dependency analysis
- Capability matching
- Candidate generation
- Plan ranking
- Business IR generation
- Replay
- Resume
- Cancellation
- Multi-tenant isolation
- Large planning sessions

---

# 26. Production Rollout

Phase 1

Planning session infrastructure.

Phase 2

Context engine.

Phase 3

Intent engine.

Phase 4

Goal decomposition.

Phase 5

Capability matching.

Phase 6

Candidate generation.

Phase 7

Evaluation engine.

Phase 8

Business IR output.

The Planner should initially operate alongside manual React Flow workflows before becoming the default planning mechanism.

---

# 27. Future Extensions

Future versions may include

- Multi-planner collaboration
- Hierarchical planners
- Specialized domain planners
- Distributed planning
- Continuous planning
- Long-running planning sessions
- Self-optimizing planners
- Industry-specific planners

The Planner Runtime should evolve independently from both the Workflow Compiler and the Execution Runtime.

Its responsibility is not execution.

Its responsibility is intelligent business reasoning.

---

# 28. Engineering Principles

The Planner Runtime is the cognitive layer of TCOS.

It reasons.

It compares.

It predicts.

It chooses.

It never executes.

Keeping planning independent from execution is the architectural decision that allows Tajeran to evolve into a true Cognitive Operating System rather than another workflow engine.# 05 Planner Runtime

> Documentation placeholder.
