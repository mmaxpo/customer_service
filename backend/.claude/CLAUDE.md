# Tajeran / TCOS — Feature Audit Workspace

This file is auto-loaded at the start of every Claude Code session in this repo.
Keep it short — it costs tokens on every single session. Anything long-lived
about a specific feature belongs in `.claude/features/`, not here.

## What TCOS is

Tajeran Cognitive Operating System (TCOS), three layers:

1. **Agentic workflow core** (`app.runtime.*`, `app.tcos.*`, `agents_runtime`) —
   auto-builds a workflow per incoming message, executes it, learns from it.
   Core vocabulary: Business IR, Planning IR, ExecutionGraph, PlanCandidate,
   VerificationConfidence, `capability.invoke`, idempotency key,
   on-conflict-do-nothing, DAG workflow engine.
2. **Product layer** (`domains/customer_service/...`) — currently customer
   service, built on top of the core.
3. **Provider layer** (`providers/shopify/...`) — currently Shopify, more
   providers planned.
4. **Platform layer** — cross-cutting, not part of the 3-layer AI model:
   accounts/workspaces/tenancy, billing, notifications, audit & security.
   Everything else depends on this layer existing and being correct.

A feature can also be `cross-layer` when it's really the seam between two of
the above (e.g. AI Actions = core capability dispatch calling into a
provider). Say so explicitly in the feature file rather than forcing it into
one bucket.

Known boundary violations to watch for while auditing (don't "fix" these
unless the feature you're auditing is specifically about them — they're a
separate cleanup effort):
- `domains/customer_service/services/` importing `app.runtime.*` internals directly
- product-layer files importing `app.tcos.*` to register planners
- `providers/shopify/runtime/` importing `app.runtime` directly

## The current job: v1 feature audit

We have a list of "final v1" features. Many are already implemented
somewhere in the codebase, at varying quality. For each feature, answer
exactly three questions:

1. **What already exists?** — concrete files/functions/classes, not "looks handled."
2. **Is it good enough for v1?** — correctness, missing edge cases, whether it
   respects the layer it lives in (see boundary list above).
3. **What's left, as a task list an engineer or agent can execute directly** —
   not "improve error handling," but "add a try/except around X in file Y
   for case Z."

## Where things live

- `.claude/features/<feature-slug>.md` — one file per feature: the spec, the
  audit result, and the task list. Created from `.claude/features/_TEMPLATE.md`.
- `.claude/AUDIT_TRACKER.md` — one row per feature, status only. Check this
  first to see what's already done before starting new work.
- `.claude/commands/next-feature.md` — the `/next-feature` slash command.
  **Start every audit session with this one** — it reads only the tracker
  (cheap), shows what's left, and asks which feature to work on before doing
  anything else. Don't open `.claude/features/` yourself before this runs.
- `.claude/commands/audit-feature.md` — the `/audit-feature <slug>` command,
  for when you already know exactly which feature to run.
- `.claude/commands/log-feature.md` — the `/log-feature` slash command, for
  adding a new feature to the backlog.

The tracker is seeded with the 25 features from the v1 spec doc. If that doc
changes, update the affected feature file(s) and tracker rows — don't
regenerate everything from scratch.

## How to run an audit without burning tokens

- **One feature per session.** Never ask for "audit all features" in one
  conversation — that forces the whole ~840-file repo through context
  repeatedly and gives shallower answers per feature, not deeper ones.
- Use `/audit-feature <slug>`. It reads only that feature's file plus the
  layer(s) it's scoped to — never the whole repo.
- Before grepping broadly, check the feature file's "Likely location" field
  first — if a teammate already narrowed it down, don't re-search from scratch.
- When a feature is trivial to check (e.g. "does endpoint X exist and return
  200") prefer a fast/cheap model. Save the more expensive model for the
  judgment call — "is this good enough, what's missing."
- Don't paste large files into the conversation to "show" them — read them
  with the file tools and only quote the relevant lines back.

## Adding a new feature to audit

Run `/log-feature` and give it the feature name/description, or add a file
manually: copy `.claude/features/_TEMPLATE.md` to
`.claude/features/<slug>.md`, fill in the spec section, and add a row to
`.claude/AUDIT_TRACKER.md`. Every coworker running Claude Code in this repo
will then pick it up automatically the next time they run `/audit-feature`.
