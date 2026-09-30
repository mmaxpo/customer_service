# 03 — Execution IR (Intermediate Representation)

**Status:** Implementation Specification

**Subsystem:** TCOS Foundation

**Owner:** Workflow Compiler

**Version:** 1.0

---

# 1. Vision

Execution IR (Intermediate Representation) is the canonical execution language of the Tajeran Runtime.

It is the output of the Workflow Compiler and the input of the Execution Runtime.

Execution IR is completely deterministic.

Unlike Business IR, it contains every execution detail required by the Runtime.

```
Natural Language

↓

Business IR

↓

Workflow Compiler

↓

Execution IR

↓

Execution Runtime
```

Execution IR is the only language understood by the Runtime.

---

# 2. Responsibilities

Execution IR owns

- Execution graph
- Runtime nodes
- Runtime edges
- Variable mapping
- Data flow
- Parallel execution
- Retry policies
- Wait conditions
- Human approval configuration
- Error routing
- Runtime metadata

Execution IR does NOT own

- Planning
- Intent
- Business goals
- Capability discovery
- Learning
- Verification decisions

---

# 3. Design Philosophy

Business IR answers

```
WHAT
```

Execution IR answers

```
HOW
```

Example

Business IR

```
Issue Refund
```

Execution IR

```
shopify.get_order

↓

router.rules

↓

shopify.refund

↓

response
```

Execution IR is implementation-aware.

---

# 4. Architecture

```
Business IR

↓

Compiler

↓

Execution IR

↓

Runtime Engine
```

Execution IR becomes the Runtime contract.

---

# 5. Core Objects

Execution IR contains

```
ExecutionGraph

ExecutionNode

ExecutionEdge

ExecutionVariable

ExecutionCondition

ExecutionMetadata

ExecutionPolicy

ExecutionCheckpoint
```

---

# 6. ExecutionGraph

Top-level runtime object.

```python
ExecutionGraph

id

version

nodes

edges

variables

metadata

entry_nodes

exit_nodes
```

This is passed directly to the Runtime.

---

# 7. ExecutionNode

Represents one runtime operation.

```python
ExecutionNode

id

node_type

config

inputs

outputs

retry_policy

timeout

parallel_group

metadata
```

Examples

```
agent.custom

shopify.refund

knowledge.search

human.approval

wait.time

router.rules

response
```

---

# 8. ExecutionEdge

Represents runtime flow.

```python
ExecutionEdge

source

target

condition

mapping

priority
```

Compiler generates edges.

---

# 9. Variables

Execution variables differ from business variables.

Example

Business Variable

```
Customer
```

Execution Variable

```
customer_id

customer_object

shopify_order

conversation_summary
```

Variables become runtime state.

---

# 10. Variable Mapping

Compiler maps

```
Business Variable

↓

Execution Variable
```

Example

```
Order

↓

shopify_order
```

Automatic.

---

# 11. Runtime Metadata

Every node contains

```
Node Version

Capability Source

Compiler Version

Created By

Estimated Cost

Estimated Latency
```

Supports debugging.

---

# 12. Retry Policy

Every node may define

```
Retry Count

Retry Delay

Exponential Backoff

Retry Conditions

Maximum Attempts
```

Uses existing Runtime support.

---

# 13. Timeout Policy

Every node defines

```
Timeout

Failure Action

Escalation

Cancellation
```

Runtime enforces.

---

# 14. Human Approval

Execution IR supports

```
Approval Type

Approvers

Timeout

Escalation

Resume Policy
```

Compiler injects approval nodes automatically.

---

# 15. Wait Nodes

Supports

```
Time Wait

Event Wait

Webhook Wait

Manual Resume

External Signal
```

Existing Runtime already supports these.

---

# 16. Parallel Execution

Execution IR explicitly marks

```
Parallel Groups
```

Runtime executes concurrently.

Compiler determines grouping.

---

# 17. Conditional Routing

Supports

```
if

switch

router.rules

router.llm
```

Already exists in Runtime.

Compiler generates routing graph.

---

# 18. Error Routing

Every node defines

```
Success

Failure

Timeout

Retry

Escalation
```

Execution never becomes undefined.

---

# 19. Checkpoints

Execution IR declares

```
Snapshot Points

Resume Points

Replay Points
```

Uses existing Runtime persistence.

---

# 20. State Mapping

Execution IR maps directly into

```
RunState

WorkflowRun

Runtime Events

Snapshots

Persistence
```

Minimal transformation.

---

# 21. Runtime Compatibility

Compiler validates

- Node exists
- Version supported
- Inputs compatible
- Outputs compatible
- Runtime features available

Before execution begins.

---

# 22. Compiler Diagnostics

Compiler emits

```
Warnings

Errors

Optimizations

Transformations

Compatibility Notes
```

Execution IR contains diagnostics.

---

# 23. Serialization

Supports

```
JSON

Compressed JSON

Versioned JSON

Snapshots

Checksums
```

Stable serialization.

---

# 24. APIs

Compiler

```python
compile()

validate()

optimize()

serialize()

deserialize()
```

Runtime

```python
execute()

resume()

cancel()

replay()
```

---

# 25. Events

Execution IR generates

```
GraphCompiled

ExecutionStarted

ExecutionPaused

ExecutionResumed

ExecutionCompleted

ExecutionFailed
```

Uses existing Runtime Event Bus.

---

# 26. Persistence

Execution IR stored alongside

```
Workflow Run

Snapshots

Events

Replay Data

Diagnostics
```

Existing persistence reused.

---

# 27. Metrics

Track

```
Node Count

Parallel Groups

Critical Path

Estimated Runtime

Estimated Cost

Estimated Tokens

Retry Count

Compiler Duration
```

Useful for optimization.

---

# 28. Observability

Execution IR powers

```
Execution Timeline

Node Graph

Runtime State

Variable Viewer

Replay

Diagnostics
```

Frontend consumes directly.

---

# 29. Security

Execution IR validates

- Tenant isolation
- Node permissions
- Secret references
- Provider permissions
- Version compatibility
- Audit logging

Execution graph becomes immutable.

---

# 30. Performance

Requirements

- Fast serialization
- Immutable graph
- Incremental compilation
- Lazy config loading
- Efficient variable lookup
- Runtime-friendly structure

---

# 31. Backend Structure

```
app/compiler/execution_ir/

    models.py

    graph.py

    nodes.py

    edges.py

    variables.py

    metadata.py

    validation.py

    serialization.py

    optimization.py

    diagnostics.py
```

---

# 32. Existing Tajeran Mapping

Already Exists

✅ Runtime Engine

✅ Workflow DAG

✅ Runtime Nodes

✅ Runtime Variables

✅ State Management

✅ Replay

✅ Resume

✅ Snapshots

✅ Events

✅ Persistence

Needs Small Extension

- Compiler output model
- Execution IR object
- Compiler diagnostics
- Variable mapping
- Graph optimization

No Runtime redesign required.

---

# 33. Manual Test Plan

Validate

- Compile Business IR
- Variable mapping
- Parallel execution
- Retry policy
- Human approval
- Wait nodes
- Replay compatibility
- Resume compatibility
- Serialization
- Diagnostics
- Runtime execution
- Failure routing

---

# 34. Production Rollout

Phase 1

Execution IR models.

Phase 2

Compiler outputs Execution IR.

Phase 3

Runtime accepts Execution IR.

Phase 4

Frontend visualizes Execution IR.

Phase 5

Business IR removed from Runtime boundary.

No Runtime logic changes required.

---

# 35. Future Extensions

Future versions may include

- Incremental compilation
- Graph optimization passes
- Static analysis
- Cost-aware compilation
- Automatic parallelization
- Provider-specific optimization
- Multi-runtime targets
- Compiler plugins

Execution IR should remain the permanent contract between the Workflow Compiler and the Tajeran Runtime, allowing the Planner and Runtime to evolve independently while preserving backward compatibility.# 03 Execution Ir

> Documentation placeholder.
