# Stage 23 — Planner Engine

Version: 0.1

Status: Core Architecture

---

# Purpose

The Planner Engine is the brain of Tajeran.

Its responsibility is NOT to execute workflows.

Its responsibility is NOT to call tools.

Its responsibility is NOT to answer users.

Its responsibility is one thing only:

> Convert an intention into the optimal executable business plan.

Everything else is delegated.

---

# The Planner Is A Compiler

One of the biggest mindset changes.

Most AI systems do this:

```
Prompt

↓

LLM

↓

Answer
```

Tajeran does this:

```
Goal

↓

Planner

↓

Business Graph

↓

Workflow Compiler

↓

Runtime

↓

Verification

↓

Result
```

The planner is much closer to a compiler than a chatbot.

---

# Planner Responsibilities

Planner owns ONLY these responsibilities.

✓ Understand goal

✓ Understand constraints

✓ Retrieve context

✓ Build task graph

✓ Optimize graph

✓ Select capabilities

✓ Estimate cost

✓ Produce executable plan

Planner never executes.

---

# Planner Inputs

The planner receives one object.

```python
PlannerRequest
```

---

Example

```python
class PlannerRequest:

    user_goal: str

    business_context: BusinessContext

    planner_context: PlannerContext

    constraints: Constraints

    execution_preferences: ExecutionPreferences

    previous_execution: ExecutionSnapshot | None
```

Everything required to think.

Nothing related to runtime.

---

# Planner Output

Planner returns

```python
PlannerResult
```

---

Example

```python
class PlannerResult:

    intent

    task_graph

    workflow_ir

    confidence

    estimated_cost

    estimated_duration

    planner_reasoning

    verification_plan
```

Notice

No runtime state.

No events.

No nodes executed.

---

# Planner Passes

Planning happens in stages.

Never one huge prompt.

```
Pass 1

Intent

↓

Pass 2

Context

↓

Pass 3

Task Decomposition

↓

Pass 4

Capability Selection

↓

Pass 5

Optimization

↓

Pass 6

Verification Planning

↓

Pass 7

Compilation
```

Each pass is independent.

---

# Pass 1

Intent Analysis

Question

```
What does the user actually want?
```

Produces

```
Intent

Goal

Entities

Constraints

Priority

Confidence
```

---

Example

Prompt

```
Refund Sarah's damaged order.
```

Produces

```
Intent

Refund Order

Entity

Sarah

Reason

Damaged

Priority

Normal
```

---

# Pass 2

Context Assembly

Planner requests

```
Business Rules

Customer History

Knowledge

Policies

Templates

Learning

Capabilities
```

Produces

```
Planner Context
```

Planner now knows the environment.

---

# Pass 3

Task Decomposition

Planner asks

```
Which business activities are required?
```

Produces

```
Read Order

↓

Check Policy

↓

Refund

↓

Notify
```

Still business language.

---

# Pass 4

Capability Matching

Planner maps tasks to capabilities.

Example

```
Refund

↓

Capability

shopify.refund
```

No runtime nodes yet.

Only capability references.

---

# Pass 5

Optimization

Planner optimizes

```
Parallel Work

↓

Cost

↓

Latency

↓

Risk

↓

Human Approval

↓

Business Policy
```

Produces optimized graph.

---

# Pass 6

Verification Planning

Planner decides

```
How will success be measured?
```

Example

Refund

↓

Verify

```
Refund Exists

Customer Notified

Audit Written
```

Verification is planned before execution.

---

# Pass 7

Compilation

Planner calls

```
Workflow Compiler
```

Produces

```
Workflow IR
```

Runtime can execute it immediately.

---

# Planner Pipeline

```
PlannerRequest

↓

Intent

↓

Context

↓

Business Graph

↓

Capability Graph

↓

Optimized Graph

↓

Verification Graph

↓

Workflow IR

↓

PlannerResult
```

---

# Internal Components

Planner is NOT one class.

Planner is many services.

```
Intent Engine

Context Builder

Task Planner

Capability Matcher

Optimizer

Verification Planner

Compiler

Cost Estimator
```

Each one independently testable.

---

# Suggested Structure

```
planner/

    engine.py

    intent/

    context/

    decomposition/

    capabilities/

    optimization/

    compiler/

    verification/

    repair/

    learning/
```

---

# Planner Engine

The engine coordinates.

```python
PlannerEngine

↓

IntentEngine

↓

ContextBuilder

↓

TaskPlanner

↓

CapabilityMatcher

↓

Optimizer

↓

VerificationPlanner

↓

Compiler
```

Each stage returns immutable objects.

---

# Planner Objects

Everything should be immutable.

Example

```python
Intent

Task

Capability

TaskGraph

WorkflowIR

VerificationPlan

PlannerContext
```

Never mutate.

Always produce new objects.

Exactly like compilers.

---

# Planner Does NOT Call LLM Randomly

Instead

```
Planner

↓

Decision

↓

Need reasoning?

↓

No

↓

Rules

Yes

↓

LLM
```

LLMs become expensive reasoning plugins.

Not the planner.

---

# Planner Decision Policy

Example

```
Need Regex?

↓

No LLM

Need Classification?

↓

Small Model

Need Complex Planning?

↓

GPT-5

Need Verification?

↓

Verifier Model
```

Every LLM invocation must have a reason.

---

# Planner Cost Awareness

Planner always estimates

```
Token Cost

Money

Latency

API Calls

Risk
```

before execution.

---

# Planner Confidence

Every plan gets confidence.

```
0.98

Execute

0.42

Ask Human
```

Confidence drives autonomy.

---

# Planner Budget

Planner receives

```python
PlanningBudget

max_cost

max_latency

max_tokens

max_llm_calls
```

Planning itself has limits.

---

# Planner Is Deterministic

The same inputs should produce the same plan whenever possible.

Randomness is minimized.

---

# Planner State Machine

```
Idle

↓

Planning

↓

Optimizing

↓

Compiling

↓

Ready

↓

Executing

↓

Finished
```

Clear lifecycle.

---

# Planner Events

Everything emits events.

```
IntentExtracted

ContextLoaded

TasksGenerated

CapabilitiesMatched

PlanOptimized

WorkflowCompiled
```

Planner debugging becomes easy.

---

# Planner Errors

Planner failures are structured.

```
IntentFailure

MissingCapability

PolicyConflict

BudgetExceeded

CompilationFailure

VerificationFailure
```

Never generic exceptions.

---

# Current Mapping to Tajeran

Already Exists

✅ Runtime

✅ Workflow IR

✅ Node Registry

✅ Tool Registry

✅ Workflow Templates

Needs Implementation

❌ Planner Engine

❌ Intent Engine

❌ Context Builder

❌ Capability Matcher

❌ Optimizer

❌ Verification Planner

❌ Compiler Frontend

---

# APIs

```python
planner.plan(

    PlannerRequest

)

↓

PlannerResult
```

Everything enters through one API.

---

# Engineering Principle

The planner should never know:

- FastAPI
- React
- HTTP
- Shopify
- Database
- Runtime scheduling

It only understands planning.

That separation is what allows Tajeran to become a true cognitive operating system instead of a monolithic AI application.

---

# Readiness

Architecture

★★★★★

Engineering Design

★★★★★

Implementation

☆☆☆☆☆

This document becomes the blueprint for the first production implementation of the planner.