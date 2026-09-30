# Self Repair System
**Version:** 0.1 (Architecture Draft)

---

# Vision

The Self Repair System is responsible for automatically recovering from failures before asking a human.

It never performs the original task.

It repairs failed execution.

```
Planner

↓

Execution

↓

Verification

↓

Failed

↓

Repair

↓

Verification

↓

Completed
```

---

# Philosophy

Humans rarely succeed on the first attempt.

They

Think

↓

Try

↓

Notice Mistake

↓

Correct

↓

Continue

AI should work exactly the same way.

---

# Why It Exists

Without repair

```
Task

↓

Failure

↓

Human
```

With repair

```
Task

↓

Failure

↓

Repair

↓

Retry

↓

Success
```

---

# Responsibilities

The Repair System owns

- error diagnosis
- recovery planning
- retry strategy
- workflow modification
- alternative capability selection
- escalation

It never replaces planning.

---

# Position

```
Planner

↓

Execution

↓

Verification

↓

Repair

↓

Verification

↓

Result
```

---

# Repair Input

Example

```json
{
    "task":"Refund Customer",

    "failure":"Refund amount exceeds order value",

    "context":{

        "order":...,

        "policy":...
    }
}
```

---

# Repair Output

```json
{
    "strategy":"Retry with corrected amount",

    "changes":[...]

}
```

or

```json
{
    "strategy":"Escalate to human"
}
```

---

# Types of Failure

## Runtime Failure

Tool timeout

Network failure

Rate limit

Database unavailable

---

## Business Failure

Order missing

Refund denied

Customer not found

---

## Agent Failure

Hallucination

No answer

Exceeded token budget

Exceeded step budget

---

## Planning Failure

Missing capability

Impossible workflow

Dependency cycle

---

## Verification Failure

Wrong answer

Policy violation

Incomplete task

Unsafe output

---

# Repair Levels

## Level 1

Retry

Same execution

---

## Level 2

Retry with backoff

---

## Level 3

Retry with different model

Example

```
GPT-5 Nano

↓

GPT-5
```

---

## Level 4

Retry with different capability

Example

```
Knowledge Search

↓

Web Search
```

---

## Level 5

Modify workflow

Insert

New node

Additional validation

Approval

---

## Level 6

Escalate

Human approval

---

# Repair Loop

```
Execute

↓

Verify

↓

Repair

↓

Execute

↓

Verify

↓

Done
```

Maximum iterations configurable.

---

# Repair Strategies

## Missing Information

Ask customer.

---

## Wrong Tool

Choose another capability.

---

## Low Confidence

Increase reasoning budget.

---

## Hallucination

Use additional retrieval.

---

## Policy Failure

Insert policy lookup before decision.

---

## Timeout

Retry later.

---

## Rate Limit

Switch provider.

---

# Workflow Repair

Sometimes

Only one node needs changing.

Example

```
Knowledge Search

↓

Agent

↓

Reply
```

Repair inserts

```
Knowledge Search

↓

Policy Validation

↓

Agent

↓

Reply
```

without rebuilding the whole workflow.

---

# Planner Repair

Planner may also fail.

Repair can ask planner

```
Plan Again

Using previous failure.
```

---

# Compiler Repair

Compiler may fail.

Repair can

Reconnect graph

Insert missing response

Insert trigger

Repair variables

---

# Agent Repair

Worker output fails verification.

Repair agent receives

Task

↓

Context

↓

Previous output

↓

Failure reason

↓

Generate improved output

---

# Tool Repair

Capability unavailable

↓

Capability Registry

↓

Find equivalent capability

↓

Retry

---

# Memory

Repair history should be stored.

Example

```
Attempt 1

↓

Attempt 2

↓

Attempt 3
```

Future planners learn from previous repairs.

---

# Learning

Long-term

Repair statistics improve planning.

Example

```
Capability A

Failure Rate

42%

↓

Planner prefers Capability B
```

---

# Escalation Policy

Not everything should be repaired forever.

Planner defines

```
Maximum Attempts

Maximum Cost

Maximum Time
```

After limits

↓

Human

---

# Repair Metrics

Track

Repair Count

Success Rate

Average Attempts

Recovered Runs

Escalations

Failure Categories

Repair Cost

---

# Current Tajeran Mapping

Existing Components

✓ Runtime Replay

✓ Resume

✓ Retry

✓ Persistence

✓ Event History

✓ Agent State

✓ Human Approval

Missing

Repair Intelligence

Repair Planner

Alternative Capability Selection

Workflow Mutation

---

# Future Capabilities

Automatic Model Routing

Capability Ranking

Alternative Tool Selection

Dynamic Workflow Mutation

Adaptive Retry Policies

Self-Optimizing Plans

Learning From Failures

---

# Assessment

Runtime Recovery

★★★★★

Persistence

★★★★★

Replay

★★★★★

Repair Intelligence

☆☆☆☆☆

Workflow Mutation

☆☆☆☆☆

Learning

☆☆☆☆☆

Overall

≈15%

The infrastructure already exists.

The intelligence layer still needs to be built.

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

Verification

↓

Result

---

# Long-Term Vision

The ultimate goal is not merely autonomous execution.

The goal is autonomous recovery.

A successful AI platform is not one that never fails.

It is one that recognizes failure, understands why it failed, repairs itself when possible, and only involves humans when genuinely necessary.

Self-repair transforms Tajeran from an execution engine into a continuously improving intelligent platform.