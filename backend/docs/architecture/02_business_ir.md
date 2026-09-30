# 02 — Business IR (Intermediate Representation)

**Status:** Implementation Specification

**Subsystem:** TCOS Foundation

**Owner:** Planner Runtime

**Version:** 1.0

---

# 1. Vision

Business IR (Intermediate Representation) is the internal language of the Planner.

Humans communicate using natural language.

The Runtime executes workflow graphs.

Neither representation is suitable for planning.

Business IR exists between them.

```
Natural Language

↓

Business IR

↓

Execution IR

↓

Execution Runtime
```

Business IR is the Planner's programming language.

---

# 2. Responsibilities

Business IR owns

- Business goals
- Business tasks
- Business dependencies
- Business constraints
- Business entities
- Business variables
- Business decisions
- Planning metadata
- Capability references

Business IR does NOT own

- Runtime nodes
- API calls
- Execution scheduling
- Retry logic
- Persistence
- Runtime state

---

# 3. Philosophy

Business IR should describe

**WHAT**

must happen.

Never

**HOW**

it executes.

Example

Business IR

```
Retrieve Customer

↓

Retrieve Order

↓

Validate Refund Policy

↓

Issue Refund

↓

Notify Customer
```

No runtime details exist.

---

# 4. Architecture

```
Intent

↓

Goals

↓

Business Tasks

↓

Business Graph

↓

Capability References

↓

Business IR

↓

Workflow Compiler
```

Business IR is completely runtime-independent.

---

# 5. Core Objects

Business IR consists of

```
BusinessPlan

BusinessGoal

BusinessTask

BusinessGraph

BusinessEdge

BusinessVariable

BusinessConstraint

BusinessDecision

BusinessMetadata
```

Everything is immutable after creation.

---

# 6. BusinessPlan

Top-level planning object.

```python
BusinessPlan

id

goal

graph

constraints

metadata

planning_version

confidence

estimated_cost

estimated_latency
```

This becomes the Compiler input.

---

# 7. BusinessGoal

Represents success.

```python
BusinessGoal

id

title

description

priority

success_conditions

owner

children

status
```

Example

```
Refund Customer

Success

Refund exists

Customer notified
```

---

# 8. BusinessTask

Atomic unit of work.

```python
BusinessTask

id

name

description

category

priority

required_capabilities

estimated_duration

estimated_cost

verification_requirements
```

Planner only creates atomic tasks.

---

# 9. Atomic Task Rule

Every BusinessTask must satisfy

- One responsibility
- One measurable outcome
- One capability owner
- One verification strategy

Otherwise

↓

Further decomposition.

---

# 10. Business Graph

Planner creates a DAG.

```
BusinessGraph

nodes

edges

entry_nodes

exit_nodes

parallel_groups

critical_path
```

Compiler consumes this graph.

---

# 11. Business Edge

Represents dependency.

```python
BusinessEdge

source

target

dependency_type

condition

priority
```

Types

```
Hard

Soft

Conditional

Verification

Human
```

---

# 12. Business Variables

Planner variables.

```python
BusinessVariable

name

type

source

scope

required

default
```

Variables are business objects.

Example

```
Customer

Order

Refund

Conversation

Invoice
```

---

# 13. Business Entities

Planner understands

```
Customer

Order

Conversation

Product

Ticket

Invoice

Subscription

Payment

Document

Knowledge

Agent

Team
```

These are domain entities.

---

# 14. Constraints

Every plan carries constraints.

```python
BusinessConstraint

type

value

severity

required

reason
```

Examples

```
Budget

Compliance

Deadline

Region

Security

Approval
```

---

# 15. Decisions

Planner records important decisions.

```python
BusinessDecision

question

selected_option

alternatives

confidence

reasoning_summary
```

Useful for explainability.

---

# 16. Capability References

Business IR never stores runtime nodes.

Instead

```python
CapabilityReference

capability_id

version

confidence

alternatives
```

Compiler resolves implementation later.

---

# 17. Metadata

Every object carries

```
Planner Version

Timestamp

Confidence

Estimated Cost

Estimated Latency

Estimated Success

Planning Strategy
```

---

# 18. Graph Validation

Business IR validates

- DAG integrity
- No cycles
- Reachable exit
- Atomic tasks
- Valid capabilities
- Valid constraints

Before compilation.

---

# 19. Serialization

Every object supports

```
JSON

Versioned JSON

Hash

Checksum

Snapshot
```

Business IR becomes replayable.

---

# 20. APIs

Planner APIs

```python
create_plan()

validate_plan()

serialize()

deserialize()

snapshot()

compare()

clone()
```

Compiler API

```python
compile(plan)
```

---

# 21. Events

Publishes

```
BusinessPlanCreated

TaskAdded

TaskRemoved

ConstraintAdded

DecisionMade

CapabilityAssigned

PlanValidated
```

Consumed by

- Compiler
- Learning
- Planner Timeline

---

# 22. Persistence

Suggested tables

```
business_plans

business_tasks

business_edges

business_constraints

business_decisions

business_variables
```

Immutable.

---

# 23. Metrics

Track

```
Task Count

Graph Depth

Graph Width

Critical Path

Estimated Cost

Estimated Latency

Confidence

Planning Duration
```

---

# 24. Observability

Planner UI should visualize

```
Goal

↓

Tasks

↓

Dependencies

↓

Capabilities

↓

Business Graph
```

Every planning step observable.

---

# 25. Security

Business IR enforces

- Tenant isolation
- Immutable snapshots
- Audit history
- Permission-aware planning
- Schema version compatibility

---

# 26. Performance

Requirements

- Immutable objects
- O(1) task lookup
- Efficient DAG traversal
- Incremental validation
- Lightweight serialization

Business IR should remain lightweight.

---

# 27. Backend Structure

```
app/planner/business_ir/

    models.py

    graph.py

    validation.py

    serialization.py

    metrics.py

    planner_objects.py

    constraints.py

    variables.py

    decisions.py

    events.py
```

---

# 28. Existing Tajeran Mapping

Already Exists

✅ Workflow DAG concepts

✅ Runtime Graph

✅ Runtime Variables

✅ Runtime Metadata

✅ Runtime Validation

Needs Implementation

- Business Graph
- Business Goals
- Business Tasks
- Business Decisions
- Business Variables
- Business Constraints
- Business Plan object

Can Reuse

- Existing graph validation
- Existing serialization
- Existing persistence infrastructure
- Existing metrics framework

---

# 29. Manual Test Plan

Validate

- Create BusinessPlan
- Add Tasks
- Add Dependencies
- Validate DAG
- Detect Cycles
- Serialize
- Deserialize
- Compare Plans
- Clone Plans
- Constraint Validation
- Capability References
- Snapshot Recovery

---

# 30. Production Rollout

Phase 1

Business IR models.

Phase 2

Planner outputs Business IR.

Phase 3

Compiler consumes Business IR.

Phase 4

Planner UI visualizes Business IR.

Phase 5

Learning analyzes Business IR.

No runtime changes required.

---

# 31. Future Extensions

Future versions may support

- Business plan templates
- Industry-specific Business IR
- Automatic optimization
- Collaborative planning
- Plan simulation
- Business rule synthesis
- Multi-planner collaboration

Business IR should become the universal planning language for every product built on TCOS.

It is intentionally independent of execution technology, allowing the runtime to evolve without changing how the Planner reasons.# 02 Business Ir

> Documentation placeholder.
