Register a new v1 feature to be audited later. Argument: $ARGUMENTS (a short
description of the feature, and layer/location if known).

Steps:

1. Turn $ARGUMENTS into a short kebab-case slug, e.g. "order status webhook"
   → `order-status-webhook`.
2. Copy `.claude/features/_TEMPLATE.md` to `.claude/features/<slug>.md`.
3. Fill in only the "Spec" section from $ARGUMENTS — what it should do,
   layer, likely location if guessable, acceptance criteria if given. Leave
   "Audit Result" and "Task List" untouched (empty) — do not search the
   codebase in this command, that happens in `/audit-feature`.
4. Add one row to `.claude/AUDIT_TRACKER.md` with status `not-started`.
5. Report the slug back so it can be referenced with `/audit-feature <slug>`.

This command should never take more than a couple of tool calls — no
repo-wide search, no reading other feature files.
