# Verification System
**Version:** 0.1 (Architecture Draft)

---

# Vision

The Verification System is responsible for determining whether the execution result is acceptable.

It never performs the task.

It evaluates the task.

```
Planner

↓

Execution

↓

Verification

↓

Accepted

or

Repair
```

---

# Philosophy

Workers produce.

Verifiers judge.

Never mix both responsibilities.

---

# Why It Exists

Without verification

```
LLM

↓

Answer

↓

User
```

With verification

```
LLM

↓

Answer

↓

Verifier

↓

Accept

↓

User
```

or

```
Repair

↓

Verify Again

↓

User
```

---

# Responsibilities

Verification owns

- correctness
- completeness
- consistency
- policy compliance
- hallucination detection
- confidence estimation
- approval recommendation

It never generates business outputs.

---

# Position

```
User Prompt

↓

Planner

↓

Execution Runtime

↓

Agent Runtime

↓

Verification

↓

Repair

↓

Result
```

---

# Verification Input

Example

```json
{
    "task":"Generate Customer Reply",

    "result":"Hello Sarah...",

    "context":{

        "conversation":...,

        "policy":...

    }
}
```

---

# Verification Output

```json
{
    "passed":true,

    "confidence":0.97,

    "issues":[]
}
```

or

```json
{
    "passed":false,

    "issues":[
        "Refund policy violated"
    ]
}
```

---

# Verification Levels

## Level 1

Structural

Examples

Required fields

JSON schema

Missing output

Invalid format

---

## Level 2

Business Rules

Examples

Refund exceeds order value

Customer not found

Policy mismatch

---

## Level 3

AI Verification

LLM checks

```
Is the reply correct?

Does it answer the customer?

Did it follow policy?
```

---

## Level 4

Cross Validation

Compare

```
Tool Output

↓

LLM Output
```

If inconsistent

↓

Fail

---

## Level 5

Human Approval

High-risk actions

↓

Human decides.

---

# Verification Types

## Syntax Verification

```
JSON

Schema

Required Fields
```

---

## Semantic Verification

```
Does the answer satisfy the task?
```

---

## Policy Verification

```
Company policy

Legal rules

Business rules
```

---

## Safety Verification

Check

Hallucination

Unsafe advice

Restricted actions

PII leakage

---

## Tool Verification

Compare

Tool output

↓

Agent explanation

---

# Confidence Score

Every verification returns

```
0.0

↓

1.0
```

Planner may use confidence later.

---

# Failure Reasons

Examples

```
Hallucination

Wrong policy

Missing information

Incomplete answer

Incorrect tool usage

Contradictory output
```

---

# Verification Strategies

Simple task

↓

Rule Based

Medium task

↓

Rule + LLM

Complex task

↓

Independent Verification Agent

Planner chooses.

---

# Independent Verifier

Important

Verifier should NOT reuse

the same prompt

the same reasoning

or even necessarily

the same model

used by the worker.

Fresh evaluation reduces confirmation bias.

---

# Verification Agent

Input

```
Task

↓

Context

↓

Worker Output
```

Output

```
PASS

or

FAIL
```

Nothing else.

---

# Auto Approval

Example

Confidence

0.99

↓

Policy OK

↓

Accept Automatically

---

# Escalation

Example

Confidence

0.42

↓

Repair

or

Human

---

# Verification Rules

Customer Service

Examples

✓ Reply answers customer

✓ No internal notes

✓ No false promises

✓ Uses policy correctly

✓ Professional tone

---

# Commerce

Examples

✓ Refund amount valid

✓ Order exists

✓ Currency correct

✓ Customer owns order

---

# Knowledge

Examples

✓ Sources found

✓ Citations valid

✓ No fabricated facts

---

# Planning Verification

Planner outputs

↓

Verifier checks

Missing tasks

Impossible capability

Circular dependency

Unreachable nodes

before compilation.

---

# Workflow Verification

Compiler outputs

↓

Verifier checks

Disconnected graph

Missing trigger

Missing response

Approval placement

Reachability

---

# Runtime Verification

Execution completed

↓

Verifier checks

All required nodes executed

No unresolved errors

No unfinished approvals

---

# Agent Verification

Agent output

↓

Verifier checks

Task completed

No hallucination

Tool output respected

No policy violation

---

# Verification Policies

Not every task requires

the same strictness.

Examples

Internal summary

↓

Low verification

Refund

↓

High verification

Legal advice

↓

Very High verification

Planner selects policy.

---

# Verification Cost

Verification itself costs money.

Planner should decide

whether

verification

is worth it.

---

# Current Tajeran Mapping

Existing Components

✓ Human Approval

✓ Runtime Events

✓ Agent Events

✓ Tool Outputs

✓ Structured State

These already provide excellent inputs for verification.

Missing layer

↓

Dedicated Verification Engine.

---

# Future Capabilities

Verification Rules

Verification Agents

Confidence Models

Evaluation History

Automatic Regression Checks

Business Policy Packs

Risk Scoring

Model Comparison

---

# Assessment

Runtime Signals

★★★★★

Structured Outputs

★★★★★

Policy Infrastructure

★★★★☆

Verification Engine

★☆☆☆☆

Confidence Models

☆☆☆☆☆

Automatic Acceptance

☆☆☆☆☆

Overall

≈20%

The foundation already exists.

The intelligence layer does not.

---

# Relationship

Planning

↓

Execution

↓

Verification

↓

Repair

↓

Final Result

---

# Long-Term Vision

Every important action in Tajeran should be verifiable.

The goal is not simply to produce outputs.

The goal is to produce outputs that can justify why they should be trusted.

Verification becomes the platform's quality gate before anything reaches the customer or triggers irreversible business actions.