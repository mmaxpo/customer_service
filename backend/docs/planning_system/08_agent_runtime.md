# Agent Runtime
**Version:** 0.1 (Architecture Draft)

---

# Vision

The Agent Runtime is responsible for intelligent execution of a single business task.

It is **not** responsible for planning the entire workflow.

It executes one task at a time.

```
Planner

↓

Business Task

↓

Agent Runtime

↓

Result
```

---

# Philosophy

An Agent should never ask

"What should I build?"

The planner already answered that.

Instead the Agent asks

"What is the best way to complete this task?"

---

# Responsibilities

The Agent Runtime owns

- reasoning
- tool selection
- tool execution
- iterative thinking
- self correction
- human approval
- producing one business output

It never owns workflow planning.

---

# Position inside Tajeran

```
User Prompt

↓

Planner

↓

Business Task Graph

↓

Workflow Compiler

↓

Execution Runtime

↓

agent.custom

↓

Agent Runtime
```

Notice

The Agent Runtime itself is just one runtime node.

---

# Agent Lifecycle

Every agent follows exactly the same lifecycle.

```
Receive Task

↓

Read Context

↓

Reason

↓

Select Tool

↓

Execute Tool

↓

Observe

↓

Reason Again

↓

Finish
```

---

# Internal Loop

```
Thought

↓

Action

↓

Observation

↓

Thought

↓

Action

↓

Finish
```

Exactly one task.

Never an entire workflow.

---

# Agent Input

Example

```json
{
    "task":"Generate customer reply",

    "context":{

        "conversation":...,

        "order":...,

        "policy":...

    }
}
```

---

# Agent Output

Example

```json
{
    "reply":"Hello Sarah..."
}
```

or

```json
{
    "decision":"Refund Approved"
}
```

One task.

One output.

---

# Agent Context

Agent receives

```
Task

Business Context

Capabilities

Memory

Runtime Metadata
```

Never raw workflow definitions.

---

# Reasoning

Reasoning should remain internal.

Runtime only stores

```
Actions

Tool Calls

Observations

Output
```

Never chain of thought.

---

# Tool Selection

The Agent chooses among allowed capabilities.

Example

```
Knowledge Search

Refund

Get Order

Shipping Status
```

It cannot call arbitrary code.

---

# Tool Registry

Every agent receives

```
Capability Registry

↓

Available Tools

↓

Schemas
```

Exactly the tools needed.

Nothing more.

---

# Restricted Tools

Example

Customer Reply Agent

Allowed

```
Knowledge Search
```

Forbidden

```
Refund

Cancel Order

Delete Customer
```

Planner determines permissions.

---

# Iteration

Agent can iterate

```
Think

↓

Search

↓

Think

↓

Reply
```

Multiple steps.

---

# Step Budget

Each agent has

```
Maximum Steps
```

Example

```
3

5

10
```

Already supported.

---

# Token Budget

Each agent has

```
Maximum Tokens
```

Already supported.

Planner should select budget.

---

# Reasoning Budget

Planner chooses

```
Low

Medium

High
```

Agent executes within budget.

---

# Verbosity

Planner controls

```
Minimal

Balanced

Detailed
```

Output only.

---

# Human Approval

Agent requests approval.

Runtime pauses.

Snapshot stored.

Later

Resume.

Already implemented.

---

# Tool Calling

Agent

↓

Tool Registry

↓

Capability

↓

Runtime Tool

↓

Observation

↓

Continue

---

# Failure Recovery

Agent can recover

```
Tool Failed

↓

Retry

↓

Alternative Tool

↓

Fail
```

without planner intervention.

---

# Agent Memory

Agent memory is temporary.

Exists only during task execution.

Long-term memory belongs elsewhere.

---

# Event Stream

Agent emits

```
Run Started

LLM Started

Tool Started

Tool Finished

Approval Requested

Completed

Failed
```

Already implemented.

---

# Persistence

Agent state stored

```
AgentRun

AgentRunEvents
```

Already implemented.

---

# Resume

Paused agent

↓

Restore State

↓

Continue Thinking

↓

Finish

Already implemented.

---

# Multi-Agent Collaboration

Agents never communicate directly.

Instead

```
Planner

↓

Task Graph

↓

Worker A

↓

Worker B

↓

Worker C
```

Communication happens through workflow state.

---

# Agent Types

Examples

## Research Agent

Goal

Collect information.

---

## Decision Agent

Goal

Choose one action.

---

## Reply Agent

Goal

Generate customer response.

---

## Classification Agent

Goal

Extract structured information.

---

## Verification Agent

Goal

Validate outputs.

---

## Repair Agent

Goal

Fix failed execution.

---

All share the same runtime.

Only prompts differ.

---

# Agent Composition

Complex workflows

↓

Many simple agents

instead of

One giant agent.

---

# Cost Optimization

Planner chooses

```
Small Model

↓

Large Model

↓

Reasoning Model
```

Agent Runtime simply executes.

---

# Safety

Agent cannot

invent tools

change workflow

create new tasks

modify execution graph

Only planner can.

---

# Current Tajeran Mapping

Current implementation already supports

✓ agent.custom

✓ tool calling

✓ approvals

✓ resume

✓ persistence

✓ events

✓ token budgets

✓ reasoning effort

✓ verbosity

✓ multiple steps

The runtime architecture is already mature.

---

# Missing Capabilities

Future additions

- Tool confidence scoring

- Dynamic tool ranking

- Reflection before finish

- Verification hook

- Retry strategies

- Model routing

- Agent specialization metadata

None require runtime redesign.

---

# Current Assessment

Agent Execution

★★★★★

Persistence

★★★★★

Events

★★★★★

Approval

★★★★★

Resume

★★★★★

Tool Calling

★★★★★

Reasoning Control

★★★★★

Reflection

★★☆☆☆

Verification

★☆☆☆☆

Repair

☆☆☆☆☆

Overall

≈90%

---

# Relationship

Planning System

↓

Business Task Graph

↓

Capability Registry

↓

Workflow Compiler

↓

Execution Runtime

↓

Agent Runtime

↓

Verification

↓

Repair

↓

Final Result

---

# Long-Term Vision

The Agent Runtime should become a universal intelligent worker.

Regardless of product—

Customer Service

Sales

Marketing

Security

Finance

Legal

IT Operations

Healthcare

the runtime remains identical.

Only

Task

Capabilities

Context

System Prompt

change.

Everything else remains stable.