# 07 — Repair Engine

**Status:** Implementation Specification

**Subsystem:** TCOS Cognitive Layer

**Owner:** Repair Runtime

**Version:** 1.0

---

# 1. Vision

The Repair Engine is responsible for recovering from failures without requiring human intervention whenever possible.

Its purpose is not simply to retry failed execution.

Its purpose is to understand why the workflow failed, determine the most appropriate recovery strategy, and safely continue toward the original business goal.

Repair transforms TCOS from an execution engine into a self-healing operating system.

---

# 2. Responsibilities

The Repair Engine owns

- Failure diagnosis
- Root cause analysis
- Repair planning
- Capability replacement
- Graph patching
- Runtime recovery
- Resume planning
- Escalation
- Repair history
- Repair metrics

The Repair Engine does NOT own

- Planning
- Runtime execution
- Verification
- Learning
- Workflow compilation

---

# 3. Philosophy

Failure is normal.

Unrecovered failure is the real problem.

Verification answers

```
Did reality match the goal?
```

Repair answers

```
How do we recover?
```

---

# 4. Architecture

```
Execution Runtime

↓

Verification Failure

↓

Failure Diagnosis

↓

Repair Planner

↓

Repair Strategy

↓

Graph Patch

↓

Resume Execution

↓

Verification
```

---

# 5. Repair Lifecycle

```
Failure Detected

↓

Load Repair Policy

↓

Diagnose

↓

Generate Repair Candidates

↓

Evaluate

↓

Select Repair

↓

Patch Workflow

↓

Resume

↓

Verify Again
```

Repair itself is deterministic.

---

# 6. Failure Model

Every failure is represented as

```python
Failure

id

type

severity

source

context

verification_report

runtime_state

timestamp
```

Failures become first-class objects.

---

# 7. Failure Categories

Supported categories

```
Execution Failure

Business Failure

Capability Failure

Provider Failure

Timeout

Policy Failure

Permission Failure

Data Failure

Human Failure

Unknown Failure
```

Different categories produce different repairs.

---

# 8. Diagnosis Engine

Diagnosis determines

```
Root Cause

↓

Contributing Factors

↓

Recoverability

↓

Repair Candidates
```

Diagnosis must occur before repair.

---

# 9. Repair Strategies

Supported strategies

```
Retry

Resume

Replace Capability

Replace Provider

Patch Graph

Skip Optional Task

Request Human Approval

Escalate

Abort Workflow

Replan
```

Retry is only one option.

---

# 10. Retry Strategy

Used when

```
Transient Failure

↓

Temporary API Failure

↓

Rate Limit

↓

Network Failure
```

Never retry permanent failures.

---

# 11. Resume Strategy

Uses existing Runtime capability.

```
Checkpoint

↓

Resume

↓

Continue
```

No duplicated execution.

---

# 12. Capability Replacement

Example

```
Primary

Shopify Search

↓

Fallback

CRM Search

↓

Fallback

Manual Lookup
```

Compiler prepares fallback metadata.

---

# 13. Provider Replacement

Example

```
LLM Provider A

↓

Unavailable

↓

LLM Provider B
```

Planner already knows alternatives.

---

# 14. Graph Patching

Repair may modify the execution graph.

Example

```
Insert Approval

↓

Continue

or

Insert Validation

↓

Resume
```

Graph patches remain auditable.

---

# 15. Replanning

Some failures require

```
Verification Failure

↓

Planner

↓

New Business Plan

↓

Compiler

↓

Execution
```

Repair can request a new plan.

---

# 16. Human Escalation

Repair escalates when

```
Low Confidence

High Risk

Policy Conflict

Business Exception

Repeated Failure
```

Humans become part of the repair strategy.

---

# 17. Repair Object

```python
RepairPlan

failure

diagnosis

strategies

selected_strategy

confidence

estimated_cost

estimated_latency

resume_point
```

---

# 18. Repair Confidence

Each strategy receives

```
Success Probability

Business Risk

Technical Risk

Cost

Latency

Overall Confidence
```

Highest confidence wins.

---

# 19. Graph Patch Object

```python
GraphPatch

nodes_added

nodes_removed

edges_added

edges_removed

variables_changed

metadata
```

Execution graph remains versioned.

---

# 20. Repair History

Store

```
Failure

Diagnosis

Repair

Outcome

Verification

Learning Feedback
```

Historical repairs improve future decisions.

---

# 21. Events

Publishes

```
FailureDetected

DiagnosisCompleted

RepairPlanned

RepairSelected

GraphPatched

ExecutionResumed

RepairSucceeded

RepairFailed

Escalated
```

Observable repair.

---

# 22. APIs

```python
diagnose()

repair()

resume()

retry()

replace_capability()

replace_provider()

replan()

escalate()
```

Primary API

```
repair_failure()
```

---

# 23. Persistence

Store

```
Repair Plans

Diagnoses

Graph Patches

Repair History

Metrics

Events
```

Supports auditing.

---

# 24. Metrics

Track

```
Repair Count

Repair Success Rate

Average Repair Time

Retry Count

Escalation Rate

Replan Rate

Most Common Failures

Most Successful Strategies
```

Learning Engine consumes these.

---

# 25. Observability

Frontend visualizes

```
Failure

↓

Diagnosis

↓

Repair Candidates

↓

Selected Repair

↓

Resume

↓

Verification
```

Every repair is explainable.

---

# 26. Security

Repair validates

- Tenant isolation
- Permission boundaries
- Safe graph patches
- Capability permissions
- Audit logging

Repairs must never violate business policy.

---

# 27. Performance

Targets

```
Diagnosis

<300 ms

Simple Repair

<500 ms

Complex Repair

<3 seconds
```

Repair should feel immediate.

---

# 28. Backend Structure

```
app/repair/

    engine.py

    diagnosis.py

    planner.py

    strategies.py

    graph_patch.py

    resume.py

    escalation.py

    persistence.py

    metrics.py

    events.py

    models.py
```

---

# 29. Existing Tajeran Mapping

Already Exists

★★★★★ Runtime Resume

★★★★★ Replay

★★★★★ Snapshots

★★★★★ Event Bus

★★★★★ Jobs

★★★★★ Runtime Persistence

★★★★☆ Runtime Retry

Needs Implementation

☆☆☆☆☆

Diagnosis Engine

☆☆☆☆☆

Repair Planner

☆☆☆☆☆

Capability Replacement

☆☆☆☆☆

Graph Patching

☆☆☆☆☆

Repair History

Reuse Existing

- Resume logic
- Replay
- Snapshots
- Runtime events
- Job infrastructure
- Persistence

Repair extends the Runtime rather than replacing it.

---

# 30. Manual Test Plan

Validate

- Retry transient failure
- Resume after checkpoint
- Replace capability
- Replace provider
- Patch execution graph
- Replan workflow
- Escalate to human
- Multi-tenant isolation
- Replay repaired workflow
- Verify repaired outcome

---

# 31. Production Rollout

Phase 1

Diagnosis models.

Phase 2

Repair strategies.

Phase 3

Capability replacement.

Phase 4

Graph patching.

Phase 5

Planner integration.

Phase 6

Learning feedback.

Initially enable repair in "recommendation mode" before allowing autonomous repair in production.

---

# 32. Future Extensions

Future versions may include

- Self-healing workflows
- Predictive failure prevention
- Automatic repair optimization
- Repair simulations
- Cross-tenant repair pattern analysis
- AI-assisted diagnosis
- Distributed repair coordination

The Repair Engine should become the autonomous recovery system of TCOS.

---

# 33. Engineering Principles

Verification identifies the gap between expectation and reality.

Repair closes that gap.

The Repair Engine should always prefer the least disruptive successful strategy.

Every repair must remain explainable, auditable, reversible, and safe.

Its goal is not simply to make execution succeed.

Its goal is to achieve the intended business outcome with the minimum necessary intervention.