# Workflow IR (Intermediate Representation)
**Version:** 0.1 (Architecture Draft)

---

# Vision

Workflow IR (Intermediate Representation) is the canonical execution language of Tajeran.

Every workflow, regardless of its origin, must eventually become Workflow IR before execution.

```
React Flow

↓

Workflow IR

↓

Runtime
```

```
Prompt

↓

Planner

↓

Workflow IR

↓

Runtime
```

```
Marketplace Template

↓

Workflow IR

↓

Runtime
```

```
API

↓

Workflow IR

↓

Runtime
```

The Runtime should only understand Workflow IR.

Nothing else.

---

# Why Workflow IR Exists

Without Workflow IR

```
Prompt

↓

Runtime
```

```
React Flow

↓

Runtime
```

```
Template

↓

Runtime
```

Every source requires special runtime logic.

The runtime becomes increasingly complex.

---

With Workflow IR

```
Everything

↓

Workflow IR

↓

Runtime
```

The Runtime becomes completely source-independent.

---

# Workflow IR Philosophy

Workflow IR is

- deterministic
- executable
- serializable
- provider-independent
- frontend-independent
- planner-independent

Workflow IR is **not**

- React Flow JSON
- Runtime DAG
- Planner output
- UI state

It is the contract between planning and execution.

---

# Pipeline

```
User Prompt

↓

Intent

↓

Goal

↓

Business Task Graph

↓

Capability Resolver

↓

Workflow IR

↓

Runtime DAG

↓

Execution
```

Planning ends here.

Execution begins here.

---

# Workflow IR Responsibilities

Workflow IR must describe

- work
- dependencies
- inputs
- outputs
- execution requirements
- policies

Workflow IR must not describe

- UI
- layout
- colors
- drag positions
- frontend state

---

# Workflow IR Object

Example

```json
{
    "workflow_id":"refund_workflow",

    "version":"1.0",

    "steps":[

        {
            "id":"step_1",

            "capability":"conversation.read"
        },

        {
            "id":"step_2",

            "capability":"order.read",

            "depends_on":[
                "step_1"
            ]
        },

        {
            "id":"step_3",

            "capability":"knowledge.search",

            "depends_on":[
                "step_2"
            ]
        },

        {
            "id":"step_4",

            "capability":"agent.generate",

            "depends_on":[
                "step_3"
            ]
        }
    ]
}
```

Notice

No runtime nodes.

No React Flow.

No coordinates.

Only execution intent.

---

# Workflow Step

Each Workflow IR Step represents one executable capability.

Example

```json
{
    "id":"step_3",

    "capability":"knowledge.search",

    "inputs":[
        "conversation"
    ],

    "outputs":[
        "policy"
    ],

    "depends_on":[
        "step_2"
    ]
}
```

---

# Dependencies

Workflow IR explicitly defines dependencies.

Example

```
Conversation

↓

Order

↓

Policy

↓

Decision

↓

Reply
```

The Runtime may later optimize execution.

---

# Parallel Execution

Workflow IR allows parallel work.

```
Read Order

─────┐

Read Customer

─────┤

Read Conversation

─────┘

↓

Decision
```

Planner decides business dependencies.

Runtime decides scheduling.

---

# Policies

Workflow IR should describe execution policies.

Example

```json
{
    "retry":"default",

    "timeout":"30s",

    "approval":"required",

    "stream":true
}
```

Planner doesn't execute policies.

Runtime enforces them.

---

# Inputs

Workflow IR inputs are logical.

Example

```
conversation

customer

order

policy
```

Not

```
SQL Query

HTTP Request

Redis Key
```

---

# Outputs

Outputs are business outputs.

```
refund_decision

reply

summary

risk_score
```

Not

```
JSON

HTTP Response

Python Object
```

---

# Runtime Compilation

Workflow IR

↓

Runtime Compiler

↓

Runtime Nodes

Example

```
knowledge.search

↓

KnowledgeSearchNode
```

```
agent.generate

↓

AgentCustomNode
```

```
order.read

↓

ShopifyGetOrderNode
```

Workflow IR never knows runtime classes.

---

# Relationship with React Flow

React Flow is only an editor.

```
React Flow

↓

Workflow IR
```

React Flow is **not** the execution model.

Users can still visually edit workflows.

Internally everything becomes Workflow IR.

---

# Relationship with Planner

Planner outputs Workflow IR.

Runtime consumes Workflow IR.

Planner never calls runtime directly.

---

# Relationship with Runtime

Runtime should never ask

```
Where did this workflow come from?
```

Runtime should only ask

```
What Workflow IR should I execute?
```

---

# Relationship with Business Task Graph

Business Task Graph

↓

Capability Resolver

↓

Workflow IR

Business Tasks describe work.

Workflow IR describes execution.

---

# Workflow Compiler

The Workflow Compiler transforms

```
Business Tasks

↓

Workflow IR
```

The compiler is deterministic.

No LLM reasoning should happen here.

---

# Runtime Responsibilities

Once Workflow IR reaches Runtime

Runtime owns

- scheduling
- retries
- waits
- resume
- persistence
- approvals
- replay
- cancellation
- events

Runtime no longer reasons.

---

# Existing Tajeran Mapping

Today your runtime already supports nearly everything required.

Current runtime concepts

```
Nodes

Edges

Run State

Variables

Events

Approvals

Waits

Subflows

Persistence

Replay
```

These become the execution target for Workflow IR.

Very little runtime redesign should be required.

---

# Benefits

## Source Independence

Prompt

↓

Workflow IR

↓

Runtime

React Flow

↓

Workflow IR

↓

Runtime

Same Runtime.

---

## Stable API

Frontend changes.

Planner changes.

Providers change.

Runtime remains stable.

---

## Better Testing

Workflow IR can be snapshot tested.

Compiler can be unit tested.

Runtime can be tested independently.

---

## Lower Token Usage

Planning happens once.

Execution becomes deterministic.

---

## Easier Versioning

Workflow IR

Version 1

↓

Version 2

↓

Version 3

Runtime compatibility remains manageable.

---

# Current Tajeran Assessment

Runtime Engine

★★★★★

Workflow Persistence

★★★★★

Execution DAG

★★★★★

Workflow IR

★★☆☆☆

Today Workflow IR is implicitly mixed with runtime node definitions.

The long-term architecture should introduce Workflow IR as its own stable execution contract.

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

05_workflow_compiler.md

---

# Long-Term Vision

Workflow IR becomes the universal execution language of Tajeran.

Everything—

- Prompt Planning
- React Flow
- Marketplace Templates
- AI-generated Workflows
- API-created Workflows
- Imported Workflows

must compile into Workflow IR.

The Runtime executes Workflow IR and nothing else.

This separation allows Tajeran to evolve its planning capabilities indefinitely while preserving a stable, production-grade execution engine.