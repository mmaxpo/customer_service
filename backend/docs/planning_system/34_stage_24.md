# Stage 24 — Planner Core Data Model

Version: 0.1

Status: Foundation

---

# Purpose

This document defines the canonical data model of the Tajeran Planner.

These objects are the language spoken by every planning component.

They are NOT database models.

They are NOT API schemas.

They are immutable domain objects.

Think of them like an Abstract Syntax Tree (AST) inside a compiler.

---

# Design Principles

Every planner object should be:

- Immutable
- Serializable
- Versioned
- Testable
- Independent of runtime
- Independent of LLMs
- Independent of UI

The planner should be able to run entirely from these objects.

---

# Object Hierarchy

```
PlannerRequest

↓

Intent

↓

Goal

↓

TaskGraph

↓

CapabilityGraph

↓

WorkflowIR

↓

VerificationPlan

↓

PlannerResult
```

Everything flows through these objects.

---

# PlannerRequest

The root object.

```python
PlannerRequest
```

Purpose

Represents everything the planner needs to solve a problem.

---

Structure

```python
PlannerRequest

id

user_goal

planner_context

constraints

preferences

execution_snapshot

metadata
```

PlannerRequest never changes.

---

# Intent

Purpose

Represents what the user actually wants.

Not what they typed.

---

Example

User

```
Can you refund Sarah's damaged order?
```

Intent

```
Refund Order
```

---

Structure

```python
Intent

id

type

goal

entities

constraints

priority

confidence

metadata
```

---

Example

```python
Intent(

type="refund",

goal="Refund damaged order",

entities=[

Customer("Sarah")

],

confidence=0.98

)
```

---

# Goal

Intent answers

"What?"

Goal answers

"When are we finished?"

---

Structure

```python
Goal

description

success_conditions

failure_conditions

business_value

priority
```

---

Example

```
Goal

Refund Customer

Success

Refund exists

Customer notified

Audit recorded
```

---

# Entity

Planner reasons about entities.

Examples

```
Customer

Order

Product

Ticket

Conversation

Policy

Invoice

Shipment

Subscription
```

Everything becomes an entity.

---

Structure

```python
Entity

id

type

attributes

confidence
```

---

# Task

The smallest business activity.

Examples

```
Read Order

Validate Policy

Calculate Refund

Notify Customer
```

Not runtime nodes.

Business tasks.

---

Structure

```python
Task

id

name

description

inputs

outputs

dependencies

estimated_cost

estimated_duration

risk

priority
```

---

# TaskGraph

Planner output.

Represents business logic.

---

Example

```
Read Order

↓

Check Policy

↓

Refund

↓

Notify
```

---

Structure

```python
TaskGraph

id

tasks

edges

entry_tasks

exit_tasks

metadata
```

---

TaskGraph contains zero runtime information.

---

# Capability

Capabilities are reusable business abilities.

Example

```
Refund

Search Knowledge

Read Shopify Order

Generate Reply

Send Email

Create Ticket
```

Planner uses capabilities.

Runtime uses nodes.

---

Structure

```python
Capability

id

name

description

inputs

outputs

cost

latency

approval_required

supported_tools

reliability

quality_score
```

---

Example

```
Capability

shopify.refund

Input

order_id

Output

refund

Cost

2 API Calls

Approval

Yes
```

---

# CapabilityGraph

Maps

```
Task

↓

Capability
```

---

Example

```
Refund Task

↓

Shopify Refund

↓

Notify Customer

↓

Email Capability
```

---

Structure

```python
CapabilityGraph

tasks

capabilities

bindings
```

---

# Constraint

Planner constraints.

Examples

```
Budget

Latency

Policy

Security

Compliance

Human Approval

Region
```

---

Structure

```python
Constraint

type

value

priority
```

---

Example

```
Max Cost

$0.05
```

---

# PlannerContext

Everything planner knows.

Contains

```
Business Rules

Knowledge

Customer History

Workflow Templates

Lessons

Capabilities

Policies
```

---

Structure

```python
PlannerContext

business_memory

knowledge

templates

learning

customer_context

planner_statistics

available_capabilities
```

---

# WorkflowIR

Compiler output.

Runtime input.

---

Planner never edits runtime nodes directly.

Instead

```
Task Graph

↓

WorkflowIR

↓

Runtime
```

---

Structure

```python
WorkflowIR

nodes

edges

variables

runtime_metadata

interrupts

approvals
```

---

# VerificationPlan

Planner defines verification before execution.

---

Example

```
Refund Exists

Customer Notified

Policy Respected

Audit Recorded
```

---

Structure

```python
VerificationPlan

checks

required_score

repair_policy

human_review_threshold
```

---

# PlannerEstimate

Planner predicts execution.

---

Contains

```
Duration

Cost

Tokens

Risk

Confidence
```

---

Structure

```python
PlannerEstimate

estimated_cost

estimated_tokens

estimated_duration

estimated_llm_calls

risk_score
```

---

# PlannerResult

Final planner output.

---

Structure

```python
PlannerResult

intent

goal

task_graph

capability_graph

workflow_ir

verification_plan

estimate

confidence
```

---

# PlanningSession

Represents one planning process.

---

Structure

```python
PlanningSession

request

result

events

statistics

duration

planner_version
```

---

# PlannerEvent

Everything planner does emits events.

Examples

```
IntentExtracted

TasksGenerated

CapabilitiesMatched

OptimizationFinished

CompilationFinished
```

---

Structure

```python
PlannerEvent

id

type

timestamp

payload
```

---

# RepairPlan

Produced only after verification failure.

---

Structure

```python
RepairPlan

reason

operations

confidence

estimated_cost
```

---

# LearningRecord

Stored after execution.

---

Structure

```python
LearningRecord

lesson

source

confidence

planner_version

verification_score
```

---

# Object Relationships

```
PlannerRequest

↓

Intent

↓

Goal

↓

TaskGraph

↓

CapabilityGraph

↓

WorkflowIR

↓

Execution Runtime

↓

VerificationPlan

↓

RepairPlan

↓

LearningRecord
```

Everything becomes explicit.

---

# Immutability

Every object is immutable.

Instead of

```
Modify Task
```

Planner creates

```
New Task

↓

New Graph
```

Exactly like compiler ASTs.

---

# Serialization

All planner objects must support

```python
to_dict()

from_dict()

to_json()

from_json()
```

Never tied to ORM.

---

# Versioning

Every object carries

```
schema_version
```

Planning can evolve without breaking old executions.

---

# Suggested Package

```
app/planner/core/

    request.py

    intent.py

    goal.py

    entity.py

    task.py

    task_graph.py

    capability.py

    capability_graph.py

    context.py

    workflow_ir.py

    verification.py

    estimate.py

    result.py

    events.py
```

---

# Current Readiness

Execution Runtime

★★★★★

WorkflowIR

★★★★☆

Planner Objects

☆☆☆☆☆

Implementation Difficulty

Medium

Architectural Importance

★★★★★

---

# Why This Matters

Once these objects exist, every future planner component speaks the same language.

Intent Engine produces `Intent`.

Task Planner consumes `Intent` and produces `TaskGraph`.

Capability Matcher consumes `TaskGraph` and produces `CapabilityGraph`.

Compiler consumes `CapabilityGraph` and produces `WorkflowIR`.

Verification consumes `WorkflowIR`.

Repair consumes `VerificationPlan`.

Learning consumes `PlannerResult`.

The entire autonomous platform becomes strongly typed instead of prompt-driven.

---

# Next Stage

## Stage 25 — Capability Registry

This is where we define **every business capability Tajeran knows**, how capabilities are discovered, versioned, scored, composed, and selected by the planner.

The Capability Registry becomes the planner's equivalent of a programming language's standard library.