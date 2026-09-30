# Stage 34 — Planner Internal Data Model

Version: 1.0

Status: Implementation Specification

---

# Purpose

The Planner Runtime requires its own strongly-typed internal data model.

These models represent the planner's thinking process.

They are **not** runtime objects.

They are **not** workflow objects.

They exist only during planning.

---

# Philosophy

Current Runtime owns

```
Workflow State
```

Planner owns

```
Planning State
```

These two systems are completely independent.

---

# Planner Object Hierarchy

```
PlannerSession

↓

PlannerState

↓

PlanningContext

↓

BusinessGoal

↓

BusinessTaskGraph

↓

CapabilityGraph

↓

CandidatePlans

↓

SelectedPlan

↓

VerificationPlan

↓

CompilationResult
```

Everything is immutable whenever possible.

---

# Core Objects

Planner consists of nine core objects.

```
PlannerSession

PlannerState

PlanningContext

BusinessGoal

BusinessTask

Capability

CandidatePlan

VerificationPlan

PlanningMetrics
```

---

# PlannerSession

Represents one planning execution.

```python
PlannerSession

session_id

user_id

tenant_id

created_at

updated_at

status

planner_version

planning_budget

planning_state

planning_metrics

events
```

Purpose

Owns the complete planning lifecycle.

---

# PlannerState

Represents current planner progress.

```python
PlannerState

current_phase

context

goal

task_graph

capability_graph

candidate_plans

selected_plan

verification_plan

compilation

confidence

status
```

Purpose

Represents the planner's current thinking.

---

# PlanningContext

Collected before planning begins.

```python
PlanningContext

user

tenant

conversation

business_memory

semantic_memory

episodic_memory

constraints

preferences

environment
```

Planner never queries services directly afterwards.

Everything required should exist here.

---

# BusinessGoal

Represents what success means.

```python
BusinessGoal

id

description

intent

priority

success_conditions

constraints

deadline

owner
```

Example

```
Refund Customer

Success

Refund exists

Customer notified

Audit completed
```

---

# BusinessTask

Atomic business action.

```python
BusinessTask

id

title

description

dependencies

priority

required_capabilities

verification_requirements

estimated_cost

estimated_latency
```

Business tasks know nothing about runtime nodes.

---

# BusinessTaskGraph

Planner's DAG.

```python
BusinessTaskGraph

nodes

edges

entry_tasks

exit_tasks

parallel_groups

critical_path
```

Compiler transforms this graph later.

---

# CapabilityReference

Reference to registry.

```python
CapabilityReference

capability_id

version

score

confidence

estimated_cost

estimated_latency

metadata
```

Planner never references runtime nodes.

---

# CapabilityGraph

Maps tasks to capabilities.

```python
CapabilityGraph

task_capabilities

selected_capabilities

alternatives

fallbacks
```

Planner works entirely at capability level.

---

# CandidatePlan

Planner usually generates multiple plans.

```python
CandidatePlan

id

task_graph

capability_graph

verification_plan

estimated_cost

estimated_latency

confidence

score

reasoning_summary
```

Immutable after creation.

---

# SelectedPlan

Chosen candidate.

```python
SelectedPlan

candidate_plan_id

selection_reason

ranking

confidence

approved_at
```

Only one exists.

---

# VerificationPlan

Created before execution.

```python
VerificationPlan

checks

required_evidence

confidence_threshold

repair_strategy

human_review_rules
```

Execution cannot start without this.

---

# CompilationResult

Returned by compiler.

```python
CompilationResult

execution_ir

warnings

diagnostics

estimated_runtime

graph_statistics
```

Planner stores it for replay.

---

# PlanningBudget

Limits planner.

```python
PlanningBudget

max_time

max_llm_calls

max_tokens

max_cost

max_candidate_plans
```

Planning must terminate.

---

# PlanningMetrics

Collected automatically.

```python
PlanningMetrics

planning_duration

context_duration

reasoning_duration

capability_search_duration

ranking_duration

compilation_duration

llm_calls

tokens

estimated_execution_cost

candidate_plan_count
```

Used by Learning.

---

# PlanningConfidence

Planner confidence object.

```python
PlanningConfidence

overall

intent

goal

capabilities

verification

execution

risk
```

Each dimension tracked independently.

---

# PlanningConstraint

Represents a hard or soft constraint.

```python
PlanningConstraint

id

type

severity

description

source

required
```

Examples

```
Budget

Compliance

Latency

Human Approval

Customer Policy
```

---

# PlanningWarning

Planner warnings.

```python
PlanningWarning

code

message

severity

recommendation
```

Planning continues.

---

# PlanningError

Planning failure.

```python
PlanningError

code

message

phase

recoverable

repair_strategy
```

Never use generic exceptions.

---

# PlanningEvent

Every planner action emits events.

```python
PlanningEvent

id

timestamp

phase

type

payload

duration
```

Planner becomes replayable.

---

# PlanningCheckpoint

Planner snapshots.

```python
PlanningCheckpoint

phase

planner_state

timestamp

checksum
```

Allows resume.

---

# Object Relationships

```
PlannerSession

↓

PlannerState

↓

BusinessGoal

↓

TaskGraph

↓

CapabilityGraph

↓

CandidatePlans

↓

SelectedPlan

↓

VerificationPlan

↓

CompilationResult
```

Strict ownership hierarchy.

---

# Serialization

Every object supports

```
to_dict()

from_dict()

version

checksum
```

Allows persistence.

---

# Versioning

Every object contains

```
schema_version
```

Future-proof.

---

# Persistence

Planner stores

```
Session

State

Events

Metrics

Selected Plan

Compilation Result

Checkpoints
```

Not temporary memory.

---

# Backend Structure

```
app/planner/models/

    planner_session.py

    planner_state.py

    planning_context.py

    business_goal.py

    business_task.py

    business_task_graph.py

    capability_graph.py

    candidate_plan.py

    selected_plan.py

    verification_plan.py

    planning_metrics.py

    planning_budget.py

    planning_events.py

    planning_errors.py
```

---

# Existing Tajeran Mapping

Already Exists

★★★★★ Runtime State

★★★★★ Runtime Events

★★★★★ Workflow Models

Needs Implementation

☆☆☆☆☆

Planner Models

☆☆☆☆☆

Planning Session

☆☆☆☆☆

Planning State

☆☆☆☆☆

Candidate Plans

☆☆☆☆☆

Verification Plan

---

# Engineering Principle

Planning objects describe decisions.

Runtime objects describe execution.

Never mix them.

---

# Next Stage

## Stage 35 — Planner Context Engine

The Planner cannot make intelligent decisions without building high-quality context.

The Context Engine determines:

- what information is relevant,
- what should be ignored,
- what memories to retrieve,
- what business entities matter,
- what constraints apply,
- how much context fits within the planning budget.

This becomes the perception system of the Planner.