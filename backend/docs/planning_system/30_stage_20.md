# Stage 20 — Learning System

Version: 0.1

---

# Purpose

The Learning System is the long-term intelligence of Tajeran.

Planning makes decisions.

Execution performs work.

Verification measures quality.

Repair fixes failures.

Learning improves the entire system for the next task.

Without learning every execution is isolated.

With learning every execution makes the platform better.

---

# Philosophy

Traditional workflow systems execute.

AI assistants answer.

Tajeran should evolve.

Every execution should answer:

> What did we learn?

---

# Continuous Improvement Loop

```
User Goal

↓

Planner

↓

Execution

↓

Verification

↓

Repair

↓

Learning

↓

Better Planner
```

The loop never ends.

---

# Learning Layers

Learning happens at multiple levels.

```
Execution

Planning

Tools

Policies

Business

Customers

Models

Performance
```

Each layer improves independently.

---

# What Should Be Learned?

Not conversations.

Not prompts.

Patterns.

Knowledge.

Strategies.

Performance.

---

# Learning Categories

---

## Planning Learning

Questions

```
Which plans succeed?

Which plans fail?

Which graph structures work best?
```

Example

Planner repeatedly inserts

```
Read Order

↓

Refund
```

Verification always fails.

Learning discovers

```
Need Policy Check

before Refund.
```

Planner improves automatically.

---

## Tool Learning

Questions

```
Which tool is most reliable?

Fastest?

Cheapest?

Highest quality?
```

Example

```
Tool A

98%

Tool B

71%
```

Future planner prefers Tool A.

---

## Workflow Learning

Questions

```
Which workflow finishes fastest?

Fewest repairs?

Lowest cost?

Highest customer satisfaction?
```

Planner begins selecting proven workflows.

---

## Policy Learning

Example

```
Store Credit

accepted

94%

Refund

accepted

52%
```

Planner learns better business strategies.

---

## Communication Learning

Questions

```
Which responses satisfy customers?

Which tone works best?

Which replies reduce escalations?
```

Customer experience improves over time.

---

## Verification Learning

Verifier records

```
Common hallucinations

Common failures

Common repair patterns
```

Future verification becomes smarter.

---

## Repair Learning

Repair planner records

```
Repair

↓

Success

or

Failure
```

Eventually

```
Repair Pattern Score
```

is built.

---

# Memory Levels

Not all learning belongs together.

Separate memories.

---

## Execution Memory

Stores

```
Runtime metrics

Node durations

Failures

Token usage

Costs
```

---

## Planning Memory

Stores

```
Successful plans

Failed plans

Planner confidence

Planning patterns
```

---

## Business Memory

Stores

```
Company policies

Preferences

Approved workflows

Common business behavior
```

---

## Customer Memory

Stores

```
Communication style

History

Preferences

Known issues
```

Business-specific.

---

## Organizational Memory

Stores

```
Best Practices

Templates

Playbooks

Processes
```

This becomes reusable knowledge.

---

# What Should NEVER Be Learned?

Never memorize

```
Temporary prompts

Hallucinations

Wrong repairs

Private reasoning

Incorrect facts
```

Learning must pass verification first.

---

# Learning Pipeline

```
Execution

↓

Verification

↓

Repair

↓

Extract Lessons

↓

Validate Lessons

↓

Store

↓

Planner Uses Next Time
```

---

# Lesson Extraction

Example

Execution

↓

Verifier reports

```
Planner skipped policy check.
```

Lesson

```
Policy Check required before Refund.
```

This becomes reusable.

---

# Learning Unit

Everything becomes a Lesson.

Example

```json
{
    "category":"planning",

    "lesson":"Refund requires policy validation.",

    "confidence":0.98,

    "evidence":[]
}
```

---

# Confidence

Every lesson has confidence.

```
0.35

Ignore

0.94

Promote
```

Never trust a single execution.

---

# Promotion

Learning progresses.

```
Observation

↓

Candidate

↓

Validated

↓

Production Knowledge
```

Exactly like software deployment.

---

# Learning Requires Evidence

One success

≠

Knowledge.

Example

```
Observed

3 times

↓

Candidate

↓

Observed

1200 times

↓

Production Rule
```

Evidence matters.

---

# Planner Feedback

Planner continuously receives

```
Success Rates

Repair Rates

Verification Scores

Execution Cost

Tool Reliability
```

Planning quality continuously improves.

---

# Tool Score

Every tool receives

```
Reliability

Latency

Cost

Quality
```

Planner chooses dynamically.

Example

```
Knowledge Search

0.99

Web Search

0.72
```

---

# Node Score

Each node type accumulates statistics.

Example

```
agent.custom

Execution Time

Verification Score

Repair Frequency
```

Useful for optimization.

---

# Workflow Score

Every workflow receives

```
Completion Rate

Verification Score

Repair Count

Average Cost

Average Duration
```

Planner ranks workflows.

---

# Strategy Learning

Planner compares strategies.

Example

```
Search

↓

Summarize

↓

Reply
```

versus

```
KB

↓

LLM

↓

Reply
```

Whichever consistently wins becomes preferred.

---

# Cost Learning

Planner also learns economics.

Example

```
Strategy A

$0.22

Strategy B

$0.03

Same Quality
```

Planner becomes cheaper.

---

# Token Learning

Planner observes

```
Token Usage

↓

Output Quality
```

Eventually

```
Minimum Cost

Maximum Quality
```

---

# Business Optimization

Learning discovers

```
Repeated approvals

↓

Automate

Repeated failures

↓

Require approval

Repeated manual work

↓

Create new workflow
```

The business itself evolves.

---

# Human Feedback

Humans become another signal.

Example

```
Agent edits reply.

↓

Diff analyzed.

↓

Lesson extracted.
```

The AI learns from experts.

---

# Merchant Feedback

Merchant says

```
Good Reply

Bad Reply

Wrong Decision
```

These become high-quality labels.

---

# Safe Learning

Learning never changes production immediately.

Everything passes

```
Validation

↓

Simulation

↓

Promotion
```

Exactly like CI/CD.

---

# Learning Store

Suggested structure

```
Lessons

Patterns

Policies

Metrics

Statistics

Templates

Scores

Repair History
```

---

# Suggested Backend Structure

```
app/planner/learning/

    engine.py

    lesson_store.py

    extractor.py

    promotion.py

    scorer.py

    optimizer.py

    analytics.py
```

---

# APIs

```python
learning_engine.learn(

    execution,

    verification,

    repair

)
```

Returns

```
LearningReport
```

---

# Example

Execution

↓

Refund workflow.

Verification

↓

0.99

Repair

↓

None

Learning

↓

```
Excellent Workflow

Confidence

0.99
```

Planner increases workflow ranking.

---

# Another Example

Execution

↓

Customer Reply.

Verification

↓

0.41

Repair

↓

Succeeded.

Learning

↓

```
Original strategy unreliable.

Repair strategy preferred.
```

Planner changes future planning.

---

# Relationship to Knowledge Base

Knowledge answers

```
What is true?
```

Learning answers

```
What works?
```

These are different systems.

---

# Long-Term Evolution

The planner becomes

```
More Accurate

↓

Cheaper

↓

Faster

↓

Safer

↓

More Reliable
```

without developers changing prompts.

---

# Current Tajeran Mapping

Already Exists

✅ Runtime Metrics

✅ Runtime Events

✅ Agent Events

✅ Usage Tracking

✅ Workflow History

Missing

❌ Learning Engine

❌ Lesson Store

❌ Pattern Extraction

❌ Planner Feedback

❌ Strategy Ranking

❌ Automatic Optimization

---

# MVP

Version 1

- Store execution metrics
- Store verification scores
- Store repair outcomes
- Workflow ranking
- Tool ranking
- Planner feedback API

No automatic adaptation yet.

---

# Future Vision

```
Prompt

↓

Intent

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

Learning

↓

Better Planner

↓

Better Workflow

↓

Better Business
```

The platform becomes increasingly intelligent because of experience, not because prompts are rewritten.

---

# Current Readiness

Execution Runtime

★★★★★

Planning Layer

★★★★☆

Verification

★★☆☆☆

Repair

★☆☆☆☆

Learning

☆☆☆☆☆

Continuous Self-Improvement

☆☆☆☆☆

---

# Next Investigation

## Stage 21 — Planner Memory & Knowledge Architecture

The final foundational stage before implementation.

This stage defines how Tajeran separates:
- business knowledge,
- planner memory,
- workflow templates,
- execution history,
- semantic knowledge,
- lessons,
- and organizational intelligence,

into a coherent architecture that scales to thousands of companies and millions of executions without becoming an unstructured memory system.