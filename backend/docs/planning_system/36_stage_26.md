# Stage 26 — Workflow Compiler

Version: 0.1

Status: Core Compiler Architecture

---

# Purpose

The Workflow Compiler transforms a business plan into an executable runtime workflow.

The planner thinks in business concepts.

The runtime executes workflow nodes.

The compiler translates between them.

```
User Goal

↓

Intent

↓

Task Graph

↓

Capability Graph

↓

Business IR

↓

Workflow Compiler

↓

Execution IR

↓

Runtime Engine
```

Without this layer, the planner would need to understand runtime implementation.

That is exactly what we want to avoid.

---

# Why A Compiler?

Many AI systems generate workflow JSON directly.

That creates three problems.

1.

Planner becomes coupled to runtime.

2.

Changing runtime breaks planning.

3.

Planner starts hallucinating nodes.

Instead:

Planner produces Business IR.

Compiler produces Execution IR.

Exactly like programming languages.

---

# Compiler Responsibilities

Compiler owns only these responsibilities.

✓ Resolve capabilities

✓ Select execution strategy

✓ Expand templates

✓ Insert runtime nodes

✓ Wire variables

✓ Insert approvals

✓ Insert verification

✓ Optimize graph

✓ Produce executable workflow

Compiler never executes.

---

# Compiler Pipeline

```
Business IR

↓

Capability Resolution

↓

Strategy Selection

↓

Template Expansion

↓

Node Generation

↓

Variable Wiring

↓

Optimization

↓

Approval Injection

↓

Verification Injection

↓

Execution IR
```

Every stage has one responsibility.

---

# Input

```
BusinessIR
```

Example

```
Refund Customer

↓

Notify Customer
```

No runtime nodes exist yet.

---

# Output

```
ExecutionIR
```

Example

```
trigger.message

↓

shopify.get_order

↓

policy.check

↓

human.approval

↓

shopify.refund

↓

response
```

Now runtime understands everything.

---

# Stage 1

Capability Resolution

Input

```
Refund Customer
```

Registry returns

```
Capability

Refund Order
```

Still business level.

---

# Stage 2

Execution Strategy

One capability may have multiple implementations.

Example

```
Knowledge Search

↓

Vector Search

Hybrid Search

Graph Search
```

Compiler selects one.

Selection depends on

Latency

Cost

Accuracy

Tenant configuration

Planner preferences

---

# Stage 3

Template Expansion

Capabilities expand into reusable workflow fragments.

Example

```
Refund Capability

↓

Read Order

Policy Check

Approval

Refund

Audit

Notify
```

No planner prompt needed.

---

# Stage 4

Node Generation

Compiler creates runtime nodes.

Example

```
Read Order

↓

shopify.get_order

Policy Check

↓

router.rules

Refund

↓

shopify.action

Notify

↓

response
```

Runtime finally appears.

---

# Stage 5

Variable Wiring

Compiler automatically connects outputs.

Example

```
Read Order

↓

order

↓

Policy Check

↓

refund_allowed

↓

Refund
```

Planner never manages variables.

Compiler does.

---

# Stage 6

Approval Injection

Compiler inserts approval automatically.

Example

Business Rule

```
Refund > $500
```

Compiler creates

```
policy.check

↓

human.approval

↓

shopify.refund
```

Planner never needs to know.

---

# Stage 7

Verification Injection

Compiler inserts verification nodes.

Example

```
Refund

↓

Verify Refund

↓

Notify
```

Planner defines verification.

Compiler implements it.

---

# Stage 8

Optimization

Compiler improves graph.

Possible optimizations

```
Merge nodes

Remove dead branches

Parallelize

Reuse variables

Collapse joins

Cache outputs

Remove duplicate searches
```

Exactly like code optimization.

---

# Stage 9

Execution IR

Compiler emits final graph.

Runtime executes immediately.

---

# Business IR

Business IR contains

```
Tasks

Capabilities

Constraints

Goals
```

Nothing runtime-specific.

---

# Execution IR

Execution IR contains

```
Nodes

Edges

Variables

Interrupts

Approvals

Retries

Metadata
```

Exactly what runtime already understands.

---

# Compiler Objects

```
CompilationRequest

CompilationContext

CompilationPass

CompilationResult

CompilationReport
```

---

# Compilation Passes

Every pass is isolated.

```
Pass 1

Resolve Capability

↓

Pass 2

Expand Template

↓

Pass 3

Generate Nodes

↓

Pass 4

Connect Variables

↓

Pass 5

Insert Approvals

↓

Pass 6

Insert Verification

↓

Pass 7

Optimize

↓

Pass 8

Emit ExecutionIR
```

Each pass is independently testable.

---

# Compiler Context

Compiler needs

```
Capability Registry

Runtime Catalog

Tenant Configuration

Business Rules

Planner Settings
```

Nothing else.

---

# Runtime Catalog

Compiler discovers available runtime nodes.

Today this already exists.

```
agent.custom

shopify.action

router.rules

join.all

response

knowledge.search

wait.event

human.approval

...
```

Compiler never hardcodes nodes.

---

# Compiler Rules

Example

```
Refund Capability

↓

shopify.action

config.action = refund
```

Simple mapping rules.

---

# Graph Rewriting

Compiler may rewrite graph.

Example

Planner

```
Knowledge Search

Knowledge Search
```

Compiler

```
Knowledge Search

↓

Shared Result
```

Duplicate removed.

---

# Variable Naming

Compiler owns variables.

Planner never generates

```
reply_result

order_data

refund_status
```

Compiler creates deterministic names.

---

# Retry Policies

Compiler injects retry automatically.

Example

```
Shopify API

↓

Retry 3

↓

Circuit Breaker
```

Business graph remains clean.

---

# Timeouts

Compiler inserts runtime policies.

```
Knowledge Search

↓

Timeout 10 sec

↓

Fallback
```

Planner doesn't think about infrastructure.

---

# Parallelization

Planner

```
Search Knowledge

Read Customer

Read Order
```

Compiler notices

No dependency.

Produces

```
Parallel Branches
```

Free performance.

---

# Compiler Report

Produces diagnostics.

Example

```
4 Capabilities

12 Runtime Nodes

2 Parallel Branches

1 Approval

Estimated Cost

$0.03
```

Excellent for debugging.

---

# Compilation Errors

Structured only.

```
MissingCapability

UnknownNode

MissingVariable

CycleDetected

ApprovalConflict

CompilationFailure
```

Never generic exceptions.

---

# Compiler Events

```
CapabilityResolved

TemplateExpanded

NodesGenerated

VariablesConnected

WorkflowOptimized

CompilationFinished
```

Everything observable.

---

# Testing

Compiler tests are deterministic.

Input

```
Refund Customer
```

Expected

```
shopify.action

human.approval

response
```

No LLM involved.

---

# Backend Structure

```
app/planner/compiler/

    compiler.py

    passes/

        capability_resolution.py

        template_expansion.py

        node_generation.py

        variable_wiring.py

        approval_injection.py

        verification_injection.py

        optimization.py

        emit_execution_ir.py

    ir/

        business_ir.py

        execution_ir.py

    report.py

    diagnostics.py
```

---

# Integration With Current Runtime

Today

```
React Flow

↓

Workflow JSON

↓

Runtime
```

Future

```
Prompt

↓

Planner

↓

Business IR

↓

Compiler

↓

Execution IR

↓

Runtime
```

Both entry points coexist.

Manual workflows continue working.

Prompt-generated workflows use the compiler.

One runtime.

Two authoring methods.

---

# Engineering Principle

The runtime should never know whether a workflow came from:

- React Flow
- Prompt
- Template
- API
- Another AI
- Another planner

It always receives the same Execution IR.

That keeps the execution engine simple, deterministic, and reusable.

---

# Current Tajeran Mapping

Already Exists

★★★★★ Runtime Engine

★★★★★ Node Catalog

★★★★★ Node Registry

★★★★★ Execution State

★★★★★ Persistence

Needs Implementation

☆☆☆☆☆ Business IR

☆☆☆☆☆ Execution IR

☆☆☆☆☆ Compiler Passes

☆☆☆☆☆ Graph Optimizer

☆☆☆☆☆ Variable Compiler

☆☆☆☆☆ Approval Injector

---

# Readiness

Runtime

★★★★★

Compiler Design

★★★★★

Implementation

☆☆☆☆☆

Architectural Importance

★★★★★

---

# Next Stage

## Stage 27 — Planning Algorithms

Until now we've designed the architecture.

The next stage defines **how the planner actually reasons**:

- hierarchical planning
- goal decomposition
- dependency analysis
- graph search
- constraint satisfaction
- cost-aware planning
- plan ranking
- alternative generation
- repair planning

This is where Tajeran stops being "LLM orchestration" and becomes an actual planning system.