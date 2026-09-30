# Stage 18 — Verification Engine

Version: 0.1

---

# Purpose

The Verification Engine is the quality control system of Tajeran.

Execution does not guarantee correctness.

A workflow may finish successfully while still producing the wrong business outcome.

Verification exists to answer one question:

> Did we actually accomplish the business goal?

---

# Philosophy

Traditional automation thinks

```
Executed

↓

Success
```

Tajeran thinks

```
Executed

↓

Verified

↓

Success
```

Execution is only one step.

Verification determines completion.

---

# Execution vs Verification

Execution asks

```
Did every node run?
```

Verification asks

```
Did the business objective succeed?
```

Example

```
Refund API

↓

200 OK
```

Execution

✅ Success

Verification

```
Was the correct order refunded?

Was the amount correct?

Was customer notified?

Did policy allow it?
```

Only then

Success.

---

# Verification Pipeline

```
Execution

↓

Collect Outputs

↓

Evaluate

↓

Quality Score

↓

Decision

↓

Finish

OR

Repair

OR

Escalate
```

---

# Verification Responsibilities

The engine verifies

- Business correctness
- Output quality
- Policy compliance
- Missing information
- Hallucinations
- Tool consistency
- Data consistency
- Customer communication quality
- Runtime completeness

---

# Verification Types

## Business Verification

Example

Goal

```
Refund customer.
```

Checks

```
Refund exists

Correct amount

Correct order

Correct customer
```

---

## Communication Verification

Example

Customer reply.

Checks

```
Helpful?

Accurate?

Professional?

Consistent with policy?

Hallucination-free?
```

---

## Tool Verification

Example

Planner says

```
Order read.
```

Verification

```
Did Shopify actually return an order?
```

---

## Policy Verification

Checks

```
Refund followed company policy?

Discount followed limits?

Customer eligibility respected?
```

---

## Workflow Verification

Checks

```
All required tasks completed?

No skipped mandatory steps?

Approvals finished?
```

---

# Verification Inputs

Verification sees

```
Original Goal

+

Planning Graph

+

Workflow IR

+

Execution Events

+

Runtime Outputs

+

Business Objects

+

Policies
```

Unlike worker agents,

Verifier sees everything.

---

# Verification Output

```json
{
    "passed":true,

    "score":0.97,

    "issues":[],

    "recommendations":[]
}
```

---

# Quality Score

Verification produces

```
0.0

↓

1.0
```

Example

```
Accuracy

0.98

Policy

1.00

Completeness

0.94

Overall

0.97
```

---

# Confidence

Verification also reports

```
confidence
```

Example

```
Score

0.95

Confidence

0.52
```

Low confidence may trigger human review.

---

# Explainability

Every failed verification explains

```
Why?

Which rule?

What evidence?

Suggested repair?
```

Example

```
Reply mentions refund completed.

Refund API never executed.
```

Planner can repair.

---

# Rule-Based Verification

Some verification is deterministic.

Example

```
Refund amount

must equal

Order amount
```

No LLM required.

---

# LLM Verification

Some quality checks require reasoning.

Example

```
Does this reply answer the customer's question?
```

LLM verifier.

---

# Hybrid Verification

Best practice

```
Rule Engine

+

LLM Judge

+

Business Policies

↓

Final Verification
```

Never trust one evaluator.

---

# Verifier Is Independent

Planner

↓

Worker

↓

Verifier

Different responsibilities.

Different prompts.

Different models if needed.

---

# Verification Checklist

Every execution may verify

```
Correctness

Completeness

Safety

Policy

Consistency

Quality

Business Goal

Customer Goal

Risk
```

---

# Business Goal Verification

Planner goal

```
Issue refund.
```

Execution

↓

Refund created.

Verification

↓

Customer actually eligible?

↓

Correct amount?

↓

Completed?

↓

Merchant notified?

---

# Conversation Verification

Reply generated.

Verifier checks

```
Customer question answered?

Tone acceptable?

Policy respected?

Sensitive information leaked?

Hallucination?
```

---

# Tool Consistency

Example

Worker says

```
Refund completed.
```

Tool result

```
Refund failed.
```

Verification catches contradiction.

---

# Multi-Agent Verification

Future

Multiple worker agents

↓

Verifier compares

↓

Finds disagreement

↓

Planner decides.

---

# Automatic Repair Trigger

Verification failure automatically creates

```
Repair Request
```

instead of

```
Workflow Failed.
```

Huge difference.

---

# Verification Memory

Store

```
Verification failures

↓

Common mistakes

↓

Planner learns
```

Future plans improve automatically.

---

# Verification Policies

Policies are configurable.

Example

```
Customer Reply

Minimum Score

0.90
```

Anything lower

↓

Repair.

---

# Verification Events

Runtime should emit

```
verification_started

verification_finished

verification_failed

verification_passed
```

Exactly like execution events.

---

# Current Tajeran Mapping

Already Exists

✅ Runtime Events

✅ Agent Events

✅ State Persistence

✅ Approval

✅ Timeline

✅ Metrics

Missing

❌ Verification Engine

❌ Verification Policies

❌ Rule Evaluator

❌ LLM Judge

❌ Quality Score

---

# Suggested Backend Structure

```
app/planner/verification/

    engine.py

    evaluators.py

    policies.py

    judges.py

    scoring.py

    reports.py
```

---

# Verification API

```python
report = verifier.verify(

    execution_result,

    planning_graph,

)
```

Returns

```
VerificationReport
```

---

# Example

Prompt

```
Refund damaged order.
```

Execution

↓

Refund succeeds.

Reply generated.

Verification

↓

Refund exists

✔

Reply correct

✔

Policy respected

✔

Customer question answered

✔

Overall

0.98

Workflow completed.

---

# Another Example

Execution

↓

Reply

```
Refund has been issued.
```

Verification

↓

Refund API

```
Never called.
```

Verification

↓

Failed

↓

Repair requested.

Without verification

Customer receives false information.

---

# Why This Layer Matters

Most AI systems stop after generation.

Tajeran should stop after **verification**.

That single architectural decision dramatically improves reliability for enterprise workflows.

---

# MVP

Version 1

- Rule verification
- LLM quality judge
- Verification score
- Verification report
- Repair request generation

No learning yet.

---

# Long-Term Vision

```
User Goal

↓

Planner

↓

Workflow

↓

Execution

↓

Verification

↓

Repair

↓

Verification

↓

Success
```

Execution is no longer the finish line.

Verified business success is.

---

# Current Readiness

Execution Runtime

★★★★★

Planning Layer

★★★★☆

Verification Engine

☆☆☆☆☆

Business Quality Evaluation

☆☆☆☆☆

Self-Correcting Execution

★☆☆☆☆

---

# Next Investigation

## Stage 19 — Repair Planner

This is where Tajeran becomes truly autonomous.

Instead of failing when verification detects a problem, it analyzes *why* the plan failed, determines the smallest possible correction, modifies the workflow, and retries only the affected portion rather than restarting everything.

This transforms the system from **automation** into **adaptive execution**.