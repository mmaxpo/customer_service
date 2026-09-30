# Stage 38 — Dependency & Constraint Analysis Engine

Version: 1.0

Status: Implementation Specification

---

# Purpose

The Dependency & Constraint Analysis Engine transforms a Business Task Graph into an executable planning graph.

After Goal Decomposition, the planner knows **what** tasks exist.

This engine determines

- which tasks depend on others,
- which tasks may execute in parallel,
- which constraints restrict execution,
- which risks exist,
- which path is critical.

This is the planner's scheduling intelligence.

---

# Philosophy

Tasks alone are not enough.

The planner must understand relationships.

```
Business Tasks

↓

Dependencies

↓

Constraints

↓

Execution Opportunities

↓

Optimized Planning Graph
```

Planning quality depends on graph quality.

---

# Core Principle

The planner should answer

```
What must happen first?

What can happen together?

What can never happen together?

What blocks everything else?
```

Before capability selection begins.

---

# Responsibilities

The Dependency & Constraint Engine owns

✓ Dependency analysis

✓ Constraint analysis

✓ Parallelism detection

✓ Critical path analysis

✓ Resource conflict detection

✓ Cycle detection

✓ Scheduling metadata

Nothing else.

---

# Pipeline

```
Business Task Graph

↓

Dependency Analysis

↓

Constraint Analysis

↓

Conflict Detection

↓

Parallel Group Detection

↓

Critical Path

↓

Planning Graph
```

---

# Input

Consumes

```python
BusinessTaskGraph

Tasks

Dependencies

Planning Context

Constraints

Policies
```

---

# Output

Produces

```python
PlanningGraph

dependency_graph

parallel_groups

critical_path

constraints

risks

execution_metadata
```

---

# Dependency Types

Planner understands several dependency types.

```
Hard Dependency

Soft Dependency

Data Dependency

Business Dependency

Policy Dependency

Verification Dependency
```

Each affects planning differently.

---

# Hard Dependency

Must execute first.

Example

```
Retrieve Order

↓

Refund Order
```

Cannot be reordered.

---

# Soft Dependency

Preferred ordering.

Can change if needed.

Example

```
Search Knowledge

↓

Generate Reply
```

Planner may optimize.

---

# Data Dependency

Task requires another task's output.

Example

```
Read Customer

↓

Customer Profile

↓

Recommend Action
```

Compiler later wires variables automatically.

---

# Business Dependency

Business rule dependency.

Example

```
Approval

↓

Refund
```

Independent of runtime.

---

# Policy Dependency

Created from company rules.

Example

```
GDPR Validation

↓

Export Customer Data
```

Inserted automatically.

---

# Verification Dependency

Execution depends on verification.

Example

```
Issue Refund

↓

Verify Refund

↓

Notify Customer
```

Verification becomes part of planning.

---

# Constraint Types

Planner supports

```
Business

Technical

Financial

Security

Compliance

Operational

Human

Time

Resource
```

Constraints influence plan ranking.

---

# Business Constraints

Examples

```
Refund Limit

Replacement Policy

VIP Rules

Regional Restrictions
```

---

# Technical Constraints

Examples

```
API Rate Limits

Provider Availability

Queue Capacity

System Maintenance
```

---

# Financial Constraints

Examples

```
Planning Budget

Execution Budget

Refund Maximum

Token Budget
```

Planner respects cost limits.

---

# Security Constraints

Examples

```
Permission Required

Sensitive Data

Admin Approval

Audit Required
```

Never bypassed.

---

# Compliance Constraints

Examples

```
GDPR

HIPAA

SOC2

PCI

Internal Governance
```

Automatically enforced.

---

# Operational Constraints

Examples

```
Business Hours

Team Availability

SLA Targets

Provider Health
```

Environment-aware planning.

---

# Human Constraints

Examples

```
Manager Approval

Legal Review

Finance Approval
```

Planner inserts approval tasks.

---

# Time Constraints

Examples

```
Must finish within 5 minutes

Before Friday

Before SLA expires
```

Affects scheduling.

---

# Resource Constraints

Examples

```
Single API Token

Shared Database

Rate Limited Service

Exclusive Lock
```

Planner avoids conflicts.

---

# Parallel Group Detection

Independent tasks grouped.

Example

```
Read Customer

Read Order

Search Knowledge
```

↓

```
Parallel Group 1
```

Compiler executes concurrently.

---

# Sequential Groups

Some tasks remain sequential.

Example

```
Read Order

↓

Validate

↓

Refund
```

No optimization allowed.

---

# Critical Path Analysis

Planner calculates

```
Longest dependency chain
```

Example

```
A

↓

B

↓

C

↓

D
```

Critical path drives latency estimates.

---

# Bottleneck Detection

Planner identifies

```
High Latency Tasks

Single Dependency Chains

Human Approvals

External APIs
```

Useful for optimization.

---

# Resource Conflict Detection

Example

```
Task A

↓

Uses Shopify API

Task B

↓

Uses Shopify API

Rate Limit Conflict
```

Planner schedules safely.

---

# Cycle Detection

Planner validates

```
No Circular Dependencies
```

Failure example

```
A

↓

B

↓

C

↓

A
```

Rejected immediately.

---

# Dead-End Detection

Planner detects

```
Tasks

↓

Never Reach Completion
```

Invalid graph.

---

# Reachability Analysis

Every task must

```
Reach Exit Node
```

No isolated branches.

---

# Scheduling Metadata

Generated for every task.

```python
SchedulingMetadata

earliest_start

latest_start

slack

parallel_group

critical

blocking_tasks
```

Compiler consumes this.

---

# Risk Analysis

Each dependency receives risk.

Example

```
External API

Risk

Medium

↓

Human Approval

Risk

High
```

Planner estimates execution reliability.

---

# Constraint Resolution

Conflicting constraints become structured decisions.

Example

```
Fastest

vs

Cheapest
```

Planner records trade-offs.

---

# Graph Validation

Checks

```
Cycles

Disconnected Nodes

Missing Dependencies

Constraint Violations

Invalid Critical Path
```

Planning graph must be valid.

---

# Graph Metrics

Collected

```
Dependency Count

Critical Path Length

Parallel Groups

Constraint Count

Estimated Duration

Risk Score
```

Used during ranking.

---

# Events

Engine emits

```
DependenciesAnalyzed

ConstraintsLoaded

ConflictsDetected

ParallelGroupsCreated

CriticalPathCalculated

PlanningGraphValidated
```

Fully observable.

---

# APIs

```python
analyze_dependencies()

analyze_constraints()

detect_parallelism()

calculate_critical_path()

detect_cycles()

detect_conflicts()

validate_graph()
```

Planner calls

```
analyze_planning_graph()
```

---

# Suggested Backend Structure

```
app/planner/dependency/

    engine.py

    dependency_analysis.py

    constraint_analysis.py

    critical_path.py

    parallelism.py

    scheduling.py

    conflicts.py

    validation.py

    metrics.py

    events.py
```

---

# Existing Tajeran Mapping

Already Exists

★★★★★ DAG Execution

★★★★★ Dependency Graph

★★★★★ Runtime Scheduler

★★★★★ Parallel Execution

★★★★☆ Graph Validation

Needs Implementation

☆☆☆☆☆

Business Dependency Engine

☆☆☆☆☆

Constraint Engine

☆☆☆☆☆

Critical Path Analysis

☆☆☆☆☆

Planning Scheduler

☆☆☆☆☆

Risk Analysis

---

# Engineering Principle

Execution schedules runtime nodes.

The Planner schedules business tasks.

These are different responsibilities.

The Planner never thinks in execution order.

It thinks in business dependencies.

---

# Long-Term Vision

Every future planner optimization depends on this engine.

Examples

- Automatic parallelization
- Cost-aware scheduling
- Risk-aware planning
- SLA optimization
- Human workload balancing
- Multi-agent scheduling

This engine becomes the foundation for intelligent planning decisions before any capability is selected.

---

# Next Stage

## Stage 39 — Capability Discovery & Matching Engine

The Planning Graph is now complete.

The next responsibility is finding **the best business capabilities** to satisfy every atomic task.

This engine will:

- discover candidate capabilities,
- rank competing capabilities,
- evaluate compatibility,
- consider cost, latency, reliability, and learning,
- select primary and fallback capabilities,
- build the Capability Graph.

This is where the Planner begins transforming business intent into executable business abilities.