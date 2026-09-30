# Stage 28 — Memory Architecture

Version: 0.1

Status: Cognitive Core

---

# Purpose

Memory is one of the fundamental services of the Tajeran Cognitive OS.

Every planner, worker, verifier, repair engine and learning engine depends on memory.

Memory is NOT a database.

Memory is NOT vector search.

Memory is the continuously evolving knowledge of the system.

---

# Philosophy

Humans do not have one memory.

Neither should Tajeran.

Instead:

```
Working Memory

↓

Execution Memory

↓

Business Memory

↓

Semantic Memory

↓

Episodic Memory

↓

Long-Term Learning
```

Each memory has one responsibility.

---

# Memory Stack

```
                    Planner

                       │

        ┌──────────────┼──────────────┐

        │              │              │

 Working Memory   Semantic Memory   Business Memory

        │              │              │

        └──────────────┼──────────────┘

                       │

              Episodic Memory

                       │

                Learning Memory
```

---

# Memory Principles

Memory should be

✓ Typed

✓ Versioned

✓ Searchable

✓ Explainable

✓ Composable

✓ Scoped

✓ Expirable

---

# Memory Types

Tajeran has six memory systems.

```
1

Working

2

Execution

3

Business

4

Semantic

5

Episodic

6

Learning
```

---

# Working Memory

Purpose

Temporary thinking.

Exactly like RAM.

Contains

```
Variables

Intermediate Results

Planner Objects

Candidate Plans

Runtime Outputs

Temporary Context
```

Destroyed after execution.

---

Example

```
Customer Name

Sarah

Order

#1928

Refund Eligible

True
```

Working only.

---

# Execution Memory

Stores execution state.

Example

```
Workflow State

Node Outputs

Interrupts

Retries

Events

Snapshots
```

You already built most of this.

---

# Business Memory

Stores structured business knowledge.

Example

```
Customer

Orders

Invoices

Tickets

Products

Policies

Inventory

Teams
```

This is NOT embeddings.

These are business entities.

---

# Semantic Memory

General knowledge.

Usually retrieved using

```
Hybrid Search

Embeddings

Knowledge Graph

Documents
```

Examples

```
Return Policy

FAQ

Documentation

Guides

Manuals
```

---

# Episodic Memory

Stores experiences.

Exactly like humans.

Example

```
Customer

Sarah

Asked refund

↓

Planner

Selected Plan B

↓

Refund succeeded

↓

Customer satisfied
```

Complete story.

---

# Learning Memory

Stores lessons.

Not events.

Lessons.

Example

```
Refund Plan

↓

Policy Check before Knowledge Search

↓

15% faster
```

Planner becomes smarter.

---

# Memory Scope

Every memory has scope.

```
Global

↓

Tenant

↓

Business

↓

Customer

↓

Conversation

↓

Workflow

↓

Agent

↓

Task
```

Planner chooses appropriate scope.

---

# Working Memory Lifecycle

```
Create

↓

Update

↓

Read

↓

Delete
```

Always temporary.

---

# Business Memory Lifecycle

```
Create

↓

Update

↓

Archive

↓

Delete
```

Persistent.

---

# Episodic Memory Lifecycle

```
Execution

↓

Episode

↓

Compression

↓

Long-Term Storage
```

Planner learns later.

---

# Memory Objects

Everything stored is typed.

```
MemoryItem

MemorySnapshot

MemoryReference

MemoryQuery

MemoryResult

MemoryPatch
```

---

# Memory References

Planner doesn't copy everything.

Instead

```
MemoryReference

↓

Customer

48382

↓

Order

1928
```

Small.

Efficient.

---

# Memory Queries

Planner asks

```
Find

↓

Customer Refund History
```

Not SQL.

Not Vector.

Memory service decides.

---

# Memory Retrieval

Possible retrieval engines

```
SQL

Graph

Vector

KV Store

Cache

Object Store
```

Planner never knows.

---

# Memory Ranking

Retrieved memories receive scores.

```
Recency

Importance

Confidence

Business Value

Similarity
```

Highest ranked first.

---

# Memory Aging

Not everything lives forever.

Example

```
Working Memory

Minutes

Execution Memory

Days

Episodes

Years

Learning

Forever
```

Each memory ages differently.

---

# Memory Compression

Planner does not store everything.

Instead

```
Episode

↓

Summary

↓

Lesson

↓

Archive
```

Like human memory.

---

# Memory Relationships

```
Customer

↓

Conversation

↓

Ticket

↓

Workflow

↓

Episode

↓

Learning
```

Everything connected.

---

# Planner Integration

Planner reads

```
Business Memory

Semantic Memory

Learning Memory

Episodes
```

Before planning.

---

# Runtime Integration

Runtime updates

```
Execution Memory

Working Memory
```

During execution.

---

# Verification Integration

Verifier reads

```
Execution Memory

Business Memory

Episode
```

To validate success.

---

# Repair Integration

Repair planner asks

```
Has this failed before?

↓

How was it repaired?
```

Learns from history.

---

# Learning Integration

Learning reads

```
Episode

↓

Execution

↓

Verification

↓

Customer Feedback
```

Creates lessons.

---

# Memory API

```
memory.store()

memory.retrieve()

memory.patch()

memory.delete()

memory.search()

memory.summarize()

memory.compress()

memory.archive()
```

Everything goes through Memory Service.

---

# Suggested Backend Structure

```
app/memory/

    working/

    execution/

    business/

    semantic/

    episodic/

    learning/

    retrieval/

    compression/

    ranking/

    storage/

    api.py
```

---

# Existing Tajeran Mapping

Already Exists

★★★★★ Runtime State

★★★★★ Workflow Persistence

★★★★★ Events

★★★★★ Snapshots

★★★★★ Knowledge Search

Missing

☆☆☆☆☆

Working Memory

☆☆☆☆☆

Business Memory Layer

☆☆☆☆☆

Episodes

☆☆☆☆☆

Learning Memory

☆☆☆☆☆

Memory Ranking

☆☆☆☆☆

Memory Compression

---

# Important Rule

Memory is never queried directly by the planner.

Planner only asks

```
Need

↓

Memory Service

↓

Best Memories
```

Memory Service decides

where

and

how

to retrieve them.

---

# Long-Term Vision

Eventually every execution creates an experience.

Every experience becomes knowledge.

Every knowledge improves future planning.

The system continuously becomes better without changing code.

---

# Readiness

Execution Memory

★★★★★

Knowledge Search

★★★★☆

Working Memory

★★☆☆☆

Business Memory

★★☆☆☆

Episodes

☆☆☆☆☆

Learning

☆☆☆☆☆

Importance

★★★★★

---

# Next Stage

## Stage 29 — Verification Engine

Planning decides **what should happen.**

Execution performs **what was planned.**

Verification proves **what actually happened.**

The Verification Engine will become the quality gate of the entire Cognitive OS.

Instead of trusting tools or LLM outputs, Tajeran will verify reality before declaring success.

That is one of the biggest differences between an AI assistant and a production-grade autonomous platform.