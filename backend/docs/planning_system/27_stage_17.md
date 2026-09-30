# Stage 17 — Constraint Engine

Version: 0.1

---

# Purpose

The Constraint Engine is the guardian of Tajeran.

The Planner is responsible for finding the **best plan**.

The Constraint Engine is responsible for deciding whether that plan is **allowed to exist**.

It protects the business before execution begins.

```
Planner

↓

Constraint Engine

↓

Verified Plan

↓

Workflow Generator

↓

Execution
```

Without this layer, AI is creative.

With this layer, AI becomes trustworthy.

---

# Philosophy

Most AI systems ask:

> Can I solve this?

Enterprise systems ask:

> Am I allowed to solve this?

That single difference separates demos from production platforms.

---

# Responsibility

The Constraint Engine validates every generated plan against:

- Business Rules
- Company Policies
- Security Policies
- User Permissions
- Compliance
- Budgets
- Cost Limits
- Time Limits
- Data Access
- Approval Rules
- Runtime Limits

before execution begins.

---

# The Constraint Pipeline

```
User Prompt

↓

Planner

↓

Planning Graph

↓

Constraint Engine

↓

Approved Plan

↓

Workflow Generator

↓

Execution
```

No workflow bypasses this layer.

---

# Categories of Constraints

## 1. Business Constraints

Business-specific rules.

Example

```
Refunds above $500 require manager approval.

Only premium customers receive express replacement.

Orders older than 90 days cannot be refunded.
```

---

## 2. Security Constraints

Example

```
This user cannot access finance.

This workflow cannot read payroll.

Customer PII cannot leave the organization.
```

---

## 3. Permission Constraints

Planner may generate

```
Delete Customer
```

Constraint Engine checks

```
Does this user have permission?
```

If not

Plan is rejected.

---

## 4. Provider Constraints

Planner wants

```
Create Refund
```

Merchant has no Shopify connection.

Constraint Engine detects

```
Capability unavailable.
```

Planner receives feedback before execution.

---

## 5. Budget Constraints

Example

```
Maximum

$2

or

40,000 tokens
```

Planner generates

```
Estimated

$8
```

Constraint Engine rejects or requests optimization.

---

## 6. Runtime Constraints

Examples

```
Maximum runtime

Maximum depth

Maximum parallel agents

Maximum API calls

Maximum retries
```

---

## 7. Compliance Constraints

Examples

GDPR

HIPAA

SOC2

PCI

Internal Legal Policies

Planner never reasons about these directly.

Constraint Engine enforces them.

---

## 8. Approval Constraints

Example

```
Refund

>

$500
```

↓

Approval Required

Planner doesn't insert approval.

Constraint Engine does.

---

# Constraint Types

Every constraint has metadata.

Example

```json
{
    "id":"refund_limit",

    "severity":"hard",

    "scope":"business",

    "condition":"refund > 500",

    "action":"require_approval"
}
```

---

# Hard vs Soft Constraints

Hard

Cannot be violated.

Example

```
No permission
```

↓

Workflow rejected.

---

Soft

Can be optimized.

Example

```
Too expensive.
```

↓

Planner retries with cheaper plan.

---

# Constraint Evaluation

Every plan becomes

```
Planning Graph

↓

Constraint Evaluation

↓

Constraint Report
```

---

# Constraint Report

Example

```json
{
    "passed":false,

    "violations":[

        "approval_required",

        "cost_limit"

    ]
}
```

Planner receives structured feedback.

---

# Planner Feedback Loop

Instead of failure

Constraint Engine returns

```
Rejected

↓

Reason

↓

Planner Repairs

↓

New Plan
```

Planning becomes iterative.

---

# Example

Planner

```
Refund Customer
```

Constraint Engine

```
Refund > $500

↓

Approval Required
```

Planner updates plan

↓

Approval inserted.

---

# Constraint Sources

Constraints come from many places.

```
Tenant Configuration

Company Policy

Runtime

Capabilities

Installed Providers

Role Permissions

Regulatory Rules

System Limits
```

Planner doesn't know where they came from.

---

# Constraint Registry

Every constraint lives in a registry.

Example

```
refund.max

reply.max_tokens

approval.limit

allowed_channels
```

Planner discovers them automatically.

---

# Constraint Scope

Constraint may apply to

Entire Workflow

Single Capability

Specific Provider

Specific User

Specific Tenant

Specific Department

Specific Country

---

# Dynamic Constraints

Some constraints change.

Example

```
API rate limit

↓

Current usage

↓

Temporary restriction
```

Constraint Engine evaluates at planning time.

---

# Cost Constraints

Constraint Engine estimates

```
LLM Cost

API Cost

Runtime Cost

Storage Cost

Latency
```

before execution.

---

# Data Constraints

Planner requests

```
Read Customer
```

Constraint Engine checks

```
Customer data allowed?

PII policy?

Tenant isolation?

Region restrictions?
```

---

# Security Constraints

Example

Planner generates

```
Web Search

↓

Send Customer Data
```

Constraint Engine blocks it.

---

# Constraint Composition

Multiple constraints combine.

Example

```
Refund

+

High Value Customer

+

Weekend

+

Manager Offline
```

↓

Different workflow.

---

# Explainability

Every rejected plan explains

```
What failed?

Why?

How to repair?
```

Example

```
Rejected

↓

Refund exceeds approval limit.

Insert manager approval.
```

---

# Automatic Repair Suggestions

Constraint Engine can suggest

```
Insert Approval

Reduce Context

Split Workflow

Use Cheaper Model

Use Cached Result
```

Planner receives suggestions.

---

# Current Tajeran Mapping

Already Exists

✅ Human Approval Nodes

✅ User Context

✅ Runtime Limits

✅ Token Budget

✅ Permissions

✅ Provider Availability

Missing

❌ Constraint Engine

❌ Constraint Registry

❌ Policy Evaluator

❌ Budget Evaluator

❌ Compliance Evaluator

---

# Suggested Backend Structure

```
app/planner/constraints/

    engine.py

    registry.py

    evaluator.py

    policies.py

    permissions.py

    budgets.py

    compliance.py

    reports.py
```

---

# Constraint API

Example

```python
report = constraint_engine.evaluate(

    planning_graph,

    tenant_context,

)
```

Returns

```python
ConstraintReport
```

Planner decides next action.

---

# Enterprise Example

Prompt

```
Refund every order from yesterday.
```

Planner

↓

Large workflow.

Constraint Engine

↓

Violations

```
Estimated Cost

Too High

Refund Approval Missing

Rate Limit Risk
```

Planner

↓

Creates optimized workflow.

---

# Why This Layer Matters

Without Constraint Engine

AI generates plans.

With Constraint Engine

AI generates **governed plans**.

That is the difference between consumer AI and enterprise AI.

---

# MVP

Version 1 only needs

- Permission constraints
- Approval constraints
- Capability availability
- Budget limits
- Runtime limits

No compliance engine yet.

---

# Long-Term Vision

```
User Prompt

↓

Planner

↓

Planning Graph

↓

Constraint Engine

↓

Workflow Generator

↓

Compiler

↓

Runtime

↓

Execution
```

Every workflow is guaranteed to satisfy organizational rules before a single API call is made.

---

# Current Readiness

Execution Runtime

★★★★★

Planning Architecture

★★★★☆

Constraint Engine

☆☆☆☆☆

Policy Registry

☆☆☆☆☆

Enterprise Governance

☆☆☆☆☆

---

# Next Investigation

## Stage 18 — Verification Engine

This is where Tajeran begins to behave like a senior engineer rather than an automation tool.

Instead of assuming execution was correct, it systematically verifies whether every important result actually satisfies the original business goal, detects mistakes, measures quality, and decides whether the workflow should finish, retry, repair, escalate to a human, or redesign itself.