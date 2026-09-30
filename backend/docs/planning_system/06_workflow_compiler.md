# Workflow Compiler
**Version:** 0.1 (Architecture Draft)

---

# Vision

The Workflow Compiler transforms an abstract Business Task Graph into an executable Tajeran workflow.

It is the final step before the Runtime.

```
User Prompt

↓

Intent Extraction

↓

Planner

↓

Business Task Graph

↓

Capability Resolver

↓

Workflow IR

↓

Workflow Compiler

↓

Runtime DAG

↓

Execution
```

The compiler never reasons.

It only translates.

---

# Why It Exists

The planner thinks in business concepts.

Example

```
Read Conversation

↓

Read Order

↓

Generate Decision

↓

Generate Reply
```

The Runtime executes nodes.

Example

```
trigger.message

↓

shopify.get_order

↓

agent.custom

↓

response
```

The Workflow Compiler converts one into the other.

---

# Responsibilities

The compiler is responsible for

• Building executable nodes

• Creating edges

• Injecting configuration

• Validating dependencies

• Creating runtime metadata

• Optimizing execution

It does NOT decide business logic.

---

# Inputs

Input

```
Workflow IR
```

Example

```json
{
    "tasks":[
        {
            "id":"t1",
            "capability":"conversation.read"
        },
        {
            "id":"t2",
            "capability":"shopify.order.read"
        },
        {
            "id":"t3",
            "capability":"customer.reply.generate"
        }
    ]
}
```

---

# Outputs

Output

Current Runtime Workflow

```json
{
    "nodes":[ ... ],
    "edges":[ ... ]
}
```

Exactly what execute_workflow_dag() already accepts.

---

# Compiler Pipeline

```
Workflow IR

↓

Capability Mapping

↓

Node Builder

↓

Edge Builder

↓

Optimization

↓

Validation

↓

Runtime Workflow
```

---

# Phase 1

Capability Mapping

Input

```
shopify.refund
```

Output

```
nodeType

shopify.action

action

refund
```

The planner does not know runtime nodes.

The compiler does.

---

# Phase 2

Node Builder

Example

IR

```json
{
    "capability":"shopify.refund"
}
```

Compiler

↓

```json
{
    "id":"refund",

    "nodeType":"shopify.action",

    "action":"refund"
}
```

---

# Phase 3

Edge Builder

Planner already defines dependencies.

Example

```
Read Order

↓

Refund

↓

Reply
```

Compiler builds

```
edge_1

edge_2
```

---

# Phase 4

Configuration Injection

The planner should never specify low-level runtime settings.

Compiler injects them.

Example

```
Retry Policy

Timeout

Approval Rules

Token Budget

Idempotency

Persistence
```

---

# Example

Planner

```
Generate Reply
```

Compiler creates

```json
{
    "nodeType":"agent.custom",

    "role":"final",

    "backend":"pure",

    "pattern":"tool_agent",

    "token_budget_mode":"balanced",

    "max_steps":3
}
```

Planner never sees these.

---

# Approval Injection

Capability

```
Refund
```

Registry says

```
Approval Required
```

Compiler inserts

```
Refund

↓

Human Approval

↓

Refund Execute
```

Automatically.

---

# Wait Injection

Capability

```
Wait for Customer
```

Compiler inserts

```
wait.event
```

No planner reasoning required.

---

# Retry Injection

Capability Metadata

```
Retry

3

Backoff

Exponential
```

Compiler injects runtime policy.

---

# Parallelization

Planner says

```
Read Order

Read Customer

Read Conversation
```

Compiler recognizes

Independent

↓

Parallel

instead of sequential.

---

# Merge

Compiler inserts

```
join.all
```

when required.

Planner doesn't need to know joins.

---

# Response Generation

If the graph has no explicit Response node

Compiler creates one.

---

# Trigger Injection

Every workflow begins with

```
trigger.message
```

unless another trigger already exists.

---

# Variable Mapping

Planner uses

```
Conversation
```

Compiler maps

```
vars.input
```

or

```
results.trigger
```

---

# Capability Expansion

One capability can become many nodes.

Example

```
Refund Customer
```

↓

```
Read Order

↓

Validate

↓

Approval

↓

Refund

↓

Generate Reply
```

Planner stays simple.

Compiler expands complexity.

---

# Optimization Pass

Compiler removes

Unused Nodes

↓

Duplicate Searches

↓

Duplicate Agents

↓

Duplicate Tool Calls

---

# Token Optimization

Compiler can merge

```
Three LLM Nodes
```

into

```
One Agent
```

when safe.

---

# Cost Optimization

Compiler knows

```
Cheap Model

↓

Expensive Model

↓

Knowledge Search

↓

Cached Result
```

Planner does not.

---

# Validation

Compiler validates

All Inputs Exist

All Outputs Used

No Cycles

No Missing Capability

Approval Connected

Response Exists

Reachable Graph

---

# Error Reporting

Instead of runtime failure

Compiler returns

```
Task

Generate Reply

↓

Missing Capability

customer.reply.generate
```

before execution starts.

---

# Compiler Interfaces

```python
compile(
    workflow_ir
) -> RuntimeWorkflow
```

---

# Runtime Independence

The Runtime never knows

Business Tasks

Planner

Capabilities

Intent

It only executes nodes.

---

# Existing Tajeran Mapping

Today

```
execute_workflow_dag()
```

already executes the compiled workflow.

Nothing changes.

Only the source of workflow creation changes.

---

# Future Optimizations

Compiler may

Merge agents

Split large workflows

Insert checkpoints

Insert waits

Insert caching

Insert approvals

Insert monitoring

Insert evaluation nodes

without planner involvement.

---

# Benefits

Planner remains small.

Runtime remains stable.

Compiler evolves independently.

---

# Long-Term Vision

Eventually the compiler becomes similar to a programming language compiler.

Planner writes

Business Program.

Compiler emits

Executable Workflow.

Runtime executes

without understanding why.

---

# Current Tajeran Assessment

Execution Runtime

★★★★★

Node Catalog

★★★★★

Workflow Compiler

☆☆☆☆☆

Workflow IR

☆☆☆☆☆

The Runtime is already mature. The compiler layer is almost entirely missing, but it can be built on top of the existing execution engine without major architectural changes.

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