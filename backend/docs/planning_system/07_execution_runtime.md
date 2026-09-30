# Execution Runtime
**Version:** 0.1 (Architecture Draft)

---

# Vision

The Execution Runtime is the heart of Tajeran.

Its only responsibility is to execute workflows reliably.

It never plans.

It never decides business strategy.

It never invents tools.

It simply executes an already compiled workflow.

```
Planner

↓

Business Task Graph

↓

Workflow Compiler

↓

Execution Runtime

↓

Result
```

---

# Philosophy

The runtime should be completely unaware of

- User prompts
- Business intent
- LLM planning
- Agent reasoning
- Workflow generation

It receives

```
Executable Workflow

↓

Run It
```

Nothing more.

---

# Responsibilities

The runtime owns

- Workflow execution
- Scheduling
- State transitions
- Persistence
- Replay
- Recovery
- Parallel execution
- Waiting
- Human approval
- Event streaming
- Retry
- Cancellation
- Idempotency

Everything else belongs elsewhere.

---

# Runtime Input

Input

```json
{
    "nodes":[...],
    "edges":[...]
}
```

Exactly what execute_workflow_dag() accepts today.

---

# Runtime Output

Produces

```
Updated State

Events

Node Outputs

Execution Metadata

Final Answer
```

---

# Execution Model

```
Initialize

↓

Find Runnable Nodes

↓

Execute

↓

Persist

↓

Apply Patch

↓

Continue

↓

Finished
```

---

# Runtime Loop

Pseudo Flow

```
while runnable_nodes:

    execute batch

    apply patches

    persist

    publish events

    find next batch
```

This is already how Tajeran behaves.

---

# State

Runtime owns

```
RunState
```

Containing

```
vars

memory

results

errors

meta

last
```

Everything flows through this object.

---

# Node Execution

Every node implements

```python
run(
    ctx,
    state,
    config
)
```

This abstraction should never change.

It allows

- Built-in nodes
- Agent nodes
- Shopify nodes
- Knowledge nodes
- Future nodes

to behave identically.

---

# Runtime Context

NodeCtx contains

```
User

Workflow Run

Thread

Persistence

Tools

Runtime Services

Metadata
```

Nodes never talk directly to the planner.

---

# Parallel Execution

Runtime executes independent nodes concurrently.

Example

```
Order

Knowledge

Customer

```

↓

Parallel

↓

Join

---

# Join

Runtime waits until all required parents complete.

Then executes

```
join.all
```

---

# State Patching

Nodes never mutate state directly.

Instead they return

```json
{
    "output":...,

    "patch":...
}
```

Runtime applies patches.

This guarantees deterministic execution.

---

# Event Model

Runtime emits events.

Examples

```
Run Started

Node Started

Node Finished

Run Finished

Run Failed

Run Cancelled
```

Events are immutable.

---

# Persistence

Runtime persists

Workflow State

Workflow Events

Snapshots

Execution Metadata

This allows replay.

---

# Replay

Replay should execute

without duplicating

refunds

emails

payments

tool calls

Idempotency guarantees this.

---

# Waits

Runtime supports

```
wait.time

wait.event
```

Execution pauses safely.

---

# Human Approval

Runtime pauses.

Stores snapshot.

Resumes later.

Agent state survives.

Already implemented.

---

# Cancellation

Runtime can stop

cleanly

without corrupting state.

---

# Retry

Runtime retries

recoverable failures

without replaying completed work.

---

# Side Effects

Runtime distinguishes

```
Pure Node

Side Effect Node
```

Only side effects require strict idempotency.

---

# Idempotency

Every side effect receives

```
Idempotency Key
```

Generated from

```
Workflow Run

↓

Node

↓

Execution Attempt
```

Already implemented.

---

# Agent Nodes

Runtime treats

```
agent.custom
```

exactly like every other node.

It does not understand

planning

reasoning

LLMs

Only

```
run()

↓

patch

↓

output
```

---

# Workflow Independence

Runtime does not know

Customer Service

Commerce

CRM

Sales

Marketing

It executes generic graphs.

---

# Runtime Events

Runtime publishes

```
Timeline

Audit

SSE

Metrics
```

without business knowledge.

---

# Error Handling

Failures remain local.

One node failing

does not corrupt

the execution engine.

---

# Recovery

After restart

Runtime loads

Workflow State

↓

Resumes execution

This is already one of Tajeran's strengths.

---

# Runtime APIs

Today

```
execute_workflow_dag()

pause()

resume()

cancel()

replay()
```

already form a stable runtime API.

Planner should never bypass them.

---

# Performance

The runtime should optimize

Parallelism

Persistence

Memory

Token usage

Scheduling

without planner involvement.

---

# Runtime Metrics

Track

Execution Time

Node Time

Retries

Failures

Paused Runs

Resume Count

LLM Calls

Tool Calls

Total Tokens

These metrics are execution concerns.

---

# Scaling

Multiple workers

can execute workflows simultaneously.

Planner does not care.

---

# Future Improvements

Potential additions

- Distributed scheduling
- Priority queues
- Resource-aware execution
- Adaptive concurrency
- Checkpoint compression
- Streaming execution
- Execution tracing

None require planner changes.

---

# Current Tajeran Assessment

Workflow DAG Execution

★★★★★

Parallel Execution

★★★★★

Persistence

★★★★★

Replay

★★★★★

Human Approval

★★★★★

Waits

★★★★★

Cancellation

★★★★★

Idempotency

★★★★★

Streaming

★★★★★

Execution Runtime

≈95%

The runtime is already one of the strongest components of Tajeran. Nearly all future work should occur above it rather than inside it.

---

# Relationship to Other Documents

01_tajeran_planning_system.md

↓

02_business_task_graph.md

↓

03_capability_resolver.md

↓

04_workflow_ir.md

↓

05_capability_registry.md

↓

06_workflow_compiler.md

↓

07_execution_runtime.md

↓

08_agent_runtime.md

↓

09_verification_system.md

↓

10_self_repair_system.md

---

# Long-Term Vision

The Execution Runtime should become a permanent foundation.

As planners, agents, products, and AI models evolve over the next decade, the runtime should require minimal changes.

Everything above it may evolve.

The runtime should remain stable.