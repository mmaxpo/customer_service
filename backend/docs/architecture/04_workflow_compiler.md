# 04 — Workflow Compiler

**Status:** Implementation Specification

**Subsystem:** TCOS Cognitive Layer

**Owner:** Workflow Compiler

**Version:** 1.0

---

# 1. Vision

The Workflow Compiler is the bridge between business reasoning and deterministic execution.

Its responsibility is to transform Business IR into Execution IR.

It is conceptually similar to a traditional programming language compiler.

```
Source Code

↓

Compiler

↓

Machine Code
```

TCOS

```
Business IR

↓

Workflow Compiler

↓

Execution IR
```

The Runtime never executes Business IR.

The Planner never generates Execution IR.

The Compiler owns the transformation.

---

# 2. Responsibilities

The Workflow Compiler owns

- Business IR parsing
- Capability resolution
- Graph transformation
- Variable mapping
- Runtime node generation
- Edge generation
- Optimization
- Validation
- Diagnostics
- Execution IR generation

The Compiler does NOT own

- Planning
- Runtime execution
- Verification
- Repair
- Learning
- Runtime scheduling

---

# 3. Design Philosophy

Planner thinks

```
Business
```

Runtime thinks

```
Execution
```

Compiler translates.

Nothing else.

The compiler should be completely deterministic.

Given identical Business IR it must always produce identical Execution IR.

---

# 4. Architecture

```
Business IR

↓

Parser

↓

Capability Resolver

↓

Graph Builder

↓

Optimization Passes

↓

Validation Passes

↓

Execution IR

↓

Runtime
```

Every phase has one responsibility.

---

# 5. Compiler Pipeline

```
Read Business IR

↓

Validate

↓

Resolve Capabilities

↓

Generate Runtime Nodes

↓

Generate Runtime Variables

↓

Generate Runtime Edges

↓

Inject Runtime Policies

↓

Optimize

↓

Validate Again

↓

Execution IR
```

---

# 6. Compiler Context

Compiler receives

```python
CompilerContext

business_plan

capability_registry

runtime_catalog

compiler_options

feature_flags

tenant

environment

compiler_version
```

Everything required exists inside CompilerContext.

---

# 7. Parsing

Compiler first validates

```
Business Graph

Capability References

Variables

Constraints

Dependencies
```

Invalid plans never compile.

---

# 8. Capability Resolution

Business Capability

↓

Runtime Implementation

Example

```
Retrieve Order

↓

shopify.get_order
```

Runtime node selection happens here.

---

# 9. Runtime Node Generation

Business Task

↓

Runtime Nodes

Example

```
Issue Refund

↓

Shopify Refund Node

↓

Audit Node

↓

Metrics Node
```

Planner never knows these exist.

---

# 10. Variable Mapping

Compiler transforms

```
Business Variables

↓

Runtime Variables
```

Example

```
Customer

↓

customer_id

↓

customer_object
```

Runtime receives optimized variables.

---

# 11. Edge Generation

Compiler generates

```
Execution Edges

↓

Conditional Edges

↓

Parallel Edges

↓

Error Edges
```

Runtime graph becomes executable.

---

# 12. Automatic Node Injection

Compiler automatically inserts runtime nodes.

Examples

```
Logging

Audit

Metrics

Tracing

Snapshot

Checkpoint

Retry

Policy Validation

Authentication
```

Planner never manually creates them.

---

# 13. Human Approval Injection

Business Constraint

↓

Human Approval

↓

Runtime Node

Automatically inserted.

---

# 14. Verification Injection

Compiler inserts

```
Verification Nodes

Evidence Collection

Assertions
```

Execution graph becomes verifiable.

---

# 15. Repair Injection

Compiler prepares repair metadata.

```
Primary Capability

Fallback Capability

Repair Strategy

Resume Point
```

Execution IR contains recovery information.

---

# 16. Optimization Passes

Compiler performs

```
Dead Node Removal

Constant Folding

Graph Simplification

Parallel Detection

Variable Elimination

Edge Simplification

Capability Fusion

Policy Injection

Node Ordering
```

Multiple passes supported.

---

# 17. Static Analysis

Compiler validates

- Missing variables
- Missing capabilities
- Invalid dependencies
- Unsupported runtime nodes
- Version mismatch
- Circular graphs
- Invalid policies

Before execution.

---

# 18. Diagnostics

Compiler produces

```python
CompilerDiagnostic

severity

message

location

recommendation

fix
```

Warnings do not stop compilation.

Errors do.

---

# 19. Optimization Levels

Supports

```
Debug

Standard

Optimized

Maximum

Production
```

Planner chooses.

---

# 20. Compiler Cache

Business Plan Hash

↓

Compiled Graph

↓

Cache

↓

Reuse

Large planning performance improvement.

---

# 21. Incremental Compilation

Only changed graph sections compile again.

Useful for

Planner edits

Human edits

Canvas editing

AI replanning

---

# 22. Compiler Metrics

Collect

```
Compilation Time

Optimization Time

Nodes Generated

Variables Generated

Edges Generated

Warnings

Errors

Optimization Savings
```

---

# 23. Events

Publishes

```
CompilationStarted

CapabilityResolved

NodesGenerated

OptimizationCompleted

ValidationCompleted

CompilationSucceeded

CompilationFailed
```

Observable compilation.

---

# 24. APIs

```python
compile()

validate()

optimize()

explain()

estimate()

compare()

cache()
```

Primary API

```python
compile_business_plan()
```

---

# 25. Persistence

Store

```
Compiler Version

Business Plan Hash

Execution IR

Diagnostics

Optimization Results

Compilation Metrics
```

Useful for replay.

---

# 26. Observability

Frontend should visualize

```
Business Graph

↓

Compiler

↓

Execution Graph
```

Node mapping visible.

Diagnostics visible.

Optimization visible.

---

# 27. Security

Compiler validates

- Tenant isolation
- Capability permissions
- Secret references
- Runtime permissions
- Compiler version compatibility

Compiler never injects unauthorized nodes.

---

# 28. Performance

Target

```
Small Graph

<50ms

Medium Graph

<200ms

Large Graph

<1 second
```

Supports

- Parallel optimization
- Incremental compilation
- Compiler caching
- Lazy resolution

---

# 29. Backend Structure

```
app/compiler/

    compiler.py

    parser.py

    resolver.py

    node_builder.py

    edge_builder.py

    variable_mapper.py

    optimizer.py

    validation.py

    diagnostics.py

    cache.py

    metrics.py

    events.py
```

---

# 30. Existing Tajeran Mapping

Already Exists

★★★★★ Runtime DAG

★★★★★ Runtime Nodes

★★★★★ Runtime Variables

★★★★★ Runtime State

★★★★★ Runtime Persistence

★★★★★ Runtime Events

★★★★★ Runtime Validation

Needs Implementation

☆☆☆☆☆

Workflow Compiler

☆☆☆☆☆

Business IR Parser

☆☆☆☆☆

Capability Resolver

☆☆☆☆☆

Optimization Passes

☆☆☆☆☆

Diagnostics

Reuse Existing

- Runtime engine
- Runtime catalog
- Node implementations
- Event system
- Persistence
- Jobs
- Replay
- Resume

The Runtime should remain almost unchanged.

---

# 31. Manual Test Plan

Validate

- Parse Business IR
- Resolve capabilities
- Generate nodes
- Generate edges
- Variable mapping
- Parallel compilation
- Diagnostics
- Optimization
- Static analysis
- Cache reuse
- Incremental compilation
- Runtime compatibility

---

# 32. Production Rollout

Phase 1

Compiler skeleton.

Phase 2

Capability resolution.

Phase 3

Execution IR generation.

Phase 4

Optimization passes.

Phase 5

Incremental compilation.

Phase 6

Compiler cache.

No Runtime modifications required.

---

# 33. Future Extensions

Future compiler versions may support

- Multi-runtime compilation
- Distributed execution compilation
- Cost-aware optimization
- AI-assisted optimization
- Industry-specific compiler plugins
- Visual compiler debugger
- Automatic graph refactoring
- Self-optimizing compilation

The Workflow Compiler should become the permanent translation layer between business reasoning and deterministic execution.

It should evolve independently of both the Planner and the Runtime.

---

# 34. Engineering Principles

The Workflow Compiler is not an execution engine.

It is not a planner.

It is not an optimizer.

It is a deterministic translator.

Its job is to faithfully transform Business IR into the best possible Execution IR while preserving business intent.

Every improvement to the compiler should increase execution quality without requiring changes to the Planner or the Runtime.# 04 Workflow Compiler

> Documentation placeholder.
