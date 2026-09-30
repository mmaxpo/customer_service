# Stage 16 — Planner LLM

Version: 0.1

---

# Purpose

The Planner LLM is the brain of Tajeran.

It is **not** a chatbot.

It is **not** a customer support agent.

It is **not** a code generator.

It is an AI Architect.

Its job is to transform an ambiguous human request into a structured business execution plan.

```
User Goal

↓

Planner LLM

↓

Planning Graph

↓

Workflow Generator

↓

Runtime
```

---

# Philosophy

Almost every AI product today asks one LLM to do everything.

```
Understand

↓

Plan

↓

Execute

↓

Verify

↓

Answer
```

That architecture doesn't scale.

Tajeran separates intelligence.

```
Planner LLM

↓

Worker Agents

↓

Verifier

↓

Repair

↓

Runtime
```

The Planner never executes.

It only thinks.

---

# Planner vs Worker

Planner

```
Think

Design

Choose

Delegate

Review
```

Worker

```
Execute

Search

Read

Write

Call APIs

Generate outputs
```

This separation is fundamental.

---

# Planner Responsibilities

The Planner LLM is responsible for:

- understanding intent
- understanding business goals
- identifying business objects
- identifying constraints
- selecting capabilities
- generating Planning Graph
- reviewing plans
- improving plans
- requesting clarification
- estimating cost
- estimating risk

The Planner never:

- calls Shopify
- searches databases
- generates customer replies
- executes tools

---

# Planner Input

Example

```
Customer wants a refund because the package arrived damaged.
```

Planner sees

```
Goal

Conversation

Merchant context

Business policies

Installed integrations

Available capabilities
```

---

# Planner Output

The planner never outputs text.

It outputs structured planning objects.

Example

```json
{
    "goal":"Handle refund request",

    "objects":[
        "customer",
        "order"
    ],

    "capabilities":[
        "commerce.order.read",
        "commerce.refund.create",
        "communication.reply.generate"
    ]
}
```

---

# Planner Knowledge

Planner should know:

Business concepts

Customer service

Sales

Marketing

Operations

HR

Finance

Legal

Healthcare

General workflows

It should NOT know runtime implementation.

---

# Planner Context

Planner receives multiple context layers.

```
User Prompt

+

Conversation

+

Merchant Profile

+

Installed Apps

+

Business Policies

+

Capability Graph

+

Historical Memory

+

Cost Limits
```

The planner reasons over all of them.

---

# Planner Memory

Planner maintains planning memory.

Example

Merchant always requires manager approval over $500.

Planner remembers.

Future plans automatically include approval.

---

# Planner Modes

Planner operates in multiple modes.

---

## Mode 1

Intent Extraction

```
What does the user want?
```

---

## Mode 2

Planning

```
How should we solve it?
```

---

## Mode 3

Critique

```
Is this plan correct?
```

---

## Mode 4

Repair

```
How should we improve it?
```

---

## Mode 5

Optimization

```
Can we reduce cost?

Can we reduce latency?

Can we parallelize?
```

---

# Multi-Pass Planning

Planner should never stop after one prompt.

Instead

```
Draft Plan

↓

Review

↓

Improve

↓

Validate

↓

Finalize
```

Exactly like experienced architects.

---

# Planner Does Not Produce Runtime

Important.

Planner outputs

Planning Graph

Workflow IR

Business Objects

Constraints

Capabilities

NOT runtime nodes.

---

# Planner Is Deterministic

Creativity is not the goal.

Consistency is.

The same business problem should generate nearly identical plans.

---

# Planner Prompt

Planner system prompt is very different from customer-facing prompts.

Instead of

```
Be helpful.
```

Planner receives

```
You are a business planning system.

Never execute.

Never answer the customer.

Only design execution plans.

Use available capabilities.

Respect business policies.

Optimize for correctness before speed.

Explain every planning decision internally.
```

---

# Internal Reasoning

Planner may reason internally.

Runtime never sees reasoning.

Workers never see reasoning.

Customers never see reasoning.

Only planning artifacts survive.

---

# Planner Confidence

Planner returns

```json
{
    "confidence":0.95,

    "missing_information":[]
}
```

Low confidence triggers clarification.

---

# Clarification

Planner should recognize uncertainty.

Example

```
Refund this order.
```

Unknown

Which order?

Planner asks

```
Which order would you like to refund?
```

instead of hallucinating.

---

# Planner Cost Awareness

Planner estimates

```
LLM Calls

API Calls

Runtime Cost

Latency

Human Approvals

Expected Tokens
```

before execution.

---

# Planner Risk Awareness

Planner classifies

```
Low

Medium

High

Critical
```

High-risk plans automatically receive approval requirements.

---

# Planner Explainability

Every plan should answer

```
Why does this step exist?
```

Example

```
Read Order

↓

Reason

Need order state before refund.
```

---

# Planner Self-Critic

Planner critiques itself.

```
Initial Plan

↓

Critic

↓

Improved Plan
```

Exactly like experienced engineers review designs.

---

# Planner Guardrails

Planner should never generate

Impossible plans

Unsafe plans

Unavailable capabilities

Infinite loops

Duplicate work

Missing verification

Missing approvals

---

# Planner Model

Planner does not need the biggest model.

It needs the best planning model.

Future architecture allows

Planner Model

Worker Model

Verification Model

Embedding Model

all to differ.

---

# Current Tajeran Mapping

Already Exists

✅ Runtime

✅ Agent Runtime

✅ Tool Registry

✅ Workflow Engine

✅ Approval

✅ Persistence

Missing

❌ Planner LLM

❌ Planning Prompt

❌ Planning Memory

❌ Planning Review

❌ Planning Critic

❌ Planning Confidence

---

# Suggested Backend Structure

```
app/planner/llm/

    planner.py

    prompts.py

    reviewer.py

    critic.py

    confidence.py

    memory.py
```

---

# Planner API

Example

```python
plan = planner.plan(

    prompt=user_prompt,

    context=context,

    capabilities=capability_graph,

)
```

Returns

```
Planning Graph
```

not runtime.

---

# Why This Is Powerful

Today

LLMs answer questions.

Tomorrow

LLMs design systems.

The Planner becomes the architect of execution, while the runtime becomes the construction crew.

That separation is what allows Tajeran to scale from customer support into a general business automation platform.

---

# MVP

Version 1 only needs

- Planner system prompt
- Planning Graph generation
- Capability selection
- Confidence score
- Clarification support

No self-review yet.

---

# Long-Term Vision

```
User Prompt

↓

Planner LLM

↓

Planning Graph

↓

Workflow Generator

↓

Workflow IR

↓

Compiler

↓

Runtime

↓

Workers

↓

Verification

↓

Repair

↓

Result
```

The Planner becomes the strategic brain of Tajeran.

Every workflow, every agent team, and every execution begins here.

---

# Current Readiness

Execution Runtime

★★★★★

Planning Architecture

★★★☆☆

Planner LLM

☆☆☆☆☆

Planning Critic

☆☆☆☆☆

Planning Memory

☆☆☆☆☆

---

# Next Investigation

## Stage 17 — Constraint Engine

This component ensures that every generated plan respects business rules, security policies, compliance requirements, budgets, permissions, approval thresholds, and runtime limitations **before** execution ever begins.

It is the difference between an impressive demo and an enterprise-grade AI planning system.