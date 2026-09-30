# Stage 29 — Verification Engine

Version: 0.1

Status: Cognitive Core

---

# Purpose

The Verification Engine determines whether reality matches the planner's expectations.

Planning predicts.

Execution performs.

Verification proves.

Without verification there is no autonomy.

---

# Philosophy

Current AI systems do

```
LLM Answer

↓

Return Answer
```

Tajeran does

```
Planner

↓

Execution

↓

Verification

↓

Repair

↓

Return Answer
```

Verification is mandatory.

---

# Core Principle

The planner never asks

> Did execution succeed?

Instead it asks

> Can I prove execution succeeded?

Those are completely different questions.

---

# Verification Pipeline

```
Planner

↓

Execution

↓

Collect Evidence

↓

Evaluate Evidence

↓

Confidence

↓

Pass

or

Repair

or

Human
```

---

# Responsibilities

Verification Engine owns

✓ Verify outputs

✓ Verify tool results

✓ Verify business state

✓ Verify policies

✓ Verify side effects

✓ Verify completion

✓ Trigger repair

Nothing else.

---

# Verification Sources

Verification should never depend on one source.

Possible evidence

```
Runtime State

Tool Responses

Business Database

Events

Memory

External APIs

Customer Feedback

Policies
```

The more evidence available

↓

Higher confidence.

---

# Verification Levels

Level 1

```
Syntax
```

Example

JSON valid?

---

Level 2

```
Schema
```

Refund object complete?

---

Level 3

```
Business
```

Refund actually exists?

---

Level 4

```
Cross-system
```

Refund exists

AND

Shopify agrees

AND

Audit exists

---

Level 5

```
Outcome
```

Customer actually received refund.

---

# Verification Objects

```
VerificationRequest

↓

VerificationPlan

↓

VerificationCheck

↓

Evidence

↓

VerificationResult
```

---

# Verification Plan

Generated during planning.

Example

```
Goal

Refund Customer

Checks

Refund Exists

Audit Exists

Notification Sent

Customer Eligible
```

---

# Verification Check

Every check has

```
id

description

required

source

validator

confidence

repair_strategy
```

---

# Example

```
Check

Refund Exists
```

Source

```
Shopify API
```

Validator

```
Refund ID found
```

---

# Evidence

Verification never trusts one observation.

Example

```
Evidence

Refund ID

Shopify

Confidence 1.0

↓

Audit Event

Confidence 0.95

↓

Customer Timeline

Confidence 0.90
```

Combined.

---

# Evidence Types

```
Database

API

Runtime

Memory

Document

Tool

Human

LLM
```

Each has different trust.

---

# Trust Levels

Example

```
Database

1.0

API

0.98

Runtime

0.95

Human

0.90

LLM

0.60
```

LLM is lowest.

Exactly opposite of most systems.

---

# Confidence Calculation

Verification computes

```
Evidence

↓

Weighted Score

↓

Confidence
```

Example

```
0.98

↓

Verified
```

---

# Verification States

```
Pending

↓

Running

↓

Verified

↓

Failed

↓

Repairing

↓

Escalated
```

Simple lifecycle.

---

# Verification Categories

```
Output

Business

Policy

Security

Compliance

Financial

External

Human
```

Planner decides which are required.

---

# Runtime Verification

Checks runtime itself.

Example

```
Workflow completed

All required nodes executed

No retries remaining

No interrupts pending
```

---

# Business Verification

Example

```
Refund

↓

Refund Record Exists

↓

Customer Updated

↓

Audit Written
```

---

# Tool Verification

Example

Tool returns

```
Refund Created
```

Verification asks Shopify

```
Is refund actually there?
```

Never trust tool output blindly.

---

# LLM Verification

LLM-generated content also verified.

Example

Reply

↓

Policy Check

↓

Tone Check

↓

PII Check

↓

Compliance Check

↓

Customer Context

Only then sent.

---

# Multi-Step Verification

Some workflows need many checks.

```
Refund

↓

Inventory Updated

↓

Email Sent

↓

CRM Updated

↓

Accounting Updated
```

Planner creates complete verification graph.

---

# Verification Graph

Verification itself becomes a graph.

```
Refund Exists

↓

Audit Exists

↓

Notify Exists

↓

PASS
```

This mirrors execution graphs.

---

# Verification Policies

Example

```
Financial

Strict

Customer Reply

Relaxed

Security

Strict

Medical

Very Strict
```

Different domains.

---

# Verification Budget

Planner also limits verification.

```
Maximum Time

Maximum Cost

Maximum API Calls
```

No infinite checking.

---

# Partial Success

Verification supports

```
Passed

Partially Passed

Failed
```

Useful for repair.

---

# Repair Trigger

If

```
Confidence

< 0.8
```

↓

Repair Engine starts automatically.

---

# Human Escalation

If

```
Repair Failed

↓

Human Review
```

Planner already knows this path.

---

# Verification History

Everything stored.

```
Verification

↓

Evidence

↓

Result

↓

Repair

↓

Outcome
```

Used by learning.

---

# Verification API

```
verify()

verify_capability()

verify_workflow()

verify_business_state()

verify_output()

verify_policy()

collect_evidence()
```

Planner never performs verification directly.

---

# Suggested Backend Structure

```
app/verifier/

    engine.py

    plans.py

    checks.py

    evidence.py

    validators/

    policies/

    confidence.py

    repair_trigger.py

    history.py
```

---

# Existing Tajeran Mapping

Already Exists

★★★★★ Runtime Events

★★★★★ Workflow State

★★★★★ Snapshots

★★★★★ Tool Outputs

★★★★☆ Audit

Needs Implementation

☆☆☆☆☆

Verification Engine

☆☆☆☆☆

Evidence Collector

☆☆☆☆☆

Confidence Calculator

☆☆☆☆☆

Verification Graph

☆☆☆☆☆

Repair Trigger

---

# Long-Term Vision

Eventually every execution ends with

```
Execution

↓

Verification

↓

Repair

↓

Learning
```

Not

```
Execution

↓

Done
```

That is the difference between automation and autonomy.

---

# Engineering Principle

Execution produces claims.

Verification produces facts.

The planner trusts facts.

Never claims.

---

# Readiness

Execution Runtime

★★★★★

Planner

★★☆☆☆

Verification

☆☆☆☆☆

Importance

★★★★★

---

# Next Stage

## Stage 30 — Repair Engine

Verification answers

> "Did reality match the plan?"

Repair answers

> "If not, how do we recover automatically?"

The Repair Engine transforms Tajeran from a workflow executor into a resilient autonomous system capable of adapting to failures without immediately involving humans.