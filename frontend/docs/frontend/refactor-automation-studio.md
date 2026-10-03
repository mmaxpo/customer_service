# Refactor task: split `automation_studio.py`

Give this whole file to the coding tool that will do the work.

## Goal

`backend/app/domains/customer_service/services/automation_studio.py` is 1,150
lines: one class, `AutomationStudioService` (about 900 lines), plus helpers. It
serves the Automations area of the app. It works, but one file holds five
different jobs. Split it into modules a person can read one at a time,
**without changing what it does**. This is a readability refactor, nothing else.

## Important: this file has no tests

Nothing under `backend/tests/` imports `automation_studio`. The full suite will
pass even if you break this file, so the suite alone proves nothing here. You
must build your own safety net first (see "Safety net" below) and you must not
skip it.

## What is in the file today

Module level:

- constants: `RUN_FLAG_REVIEW_TYPE`, `DRY_RUN_BLOCKED`, `MAX_OUTPUT_CHARS`,
  `_UNSUPPORTED_TEMPLATE`, `PROPOSAL_SYSTEM` (the Ask TCOS system prompt);
- pure helpers: `_humanize`, `_node_type`, `_catalog`, `_graph_view`,
  `_truncate`, `_diff`, `_needs_approval`, `_step_name`, `_validate`,
  `_edit_summary`, `_parse_json`.

`AutomationStudioService` methods, by job:

1. **Workflow list and detail**: `_subscriptions`, `_subscription`,
   `_live_graph`, `overview`, `workflow_detail`, `node_library`, `_run_stats`,
   `_routing_stats`, `_open_proposals`.
2. **Proposals (drafted changes)**: `_ensure_definition`, `_generate` (AI call),
   `create_proposal`, `_proposal_row`, `get_proposal`, `refine_proposal`,
   `publish_proposal`, `discard_proposal`.
3. **Testing a proposal on past conversations**: `_dry_run`, `test_proposal`.
4. **Version history**: `version_history`, `restore_version`.
5. **Run review**: `_recent_conversations`, `_run_summary`, `review_queue`,
   `run_detail` (124 lines, the longest method), `flag_run`, `dismiss_run`.

Who uses it:

- `backend/app/api/products/customer_service/studio.py` (the HTTP routes);
- `services/new_workflow.py` imports `AutomationStudioService`, `_catalog`,
  `_graph_view`, `_parse_json`, `_validate`, and calls `studio._generate` and
  `studio._subscription`;
- `services/conversation_translation.py` and `services/unanswered_topics.py`
  import `_parse_json`;
- `services/customer_feedback.py` imports `RUN_FLAG_REVIEW_TYPE`.

## Suggested shape (adjust if you find something cleaner)

- Pure graph helpers (`_graph_view`, `_diff`, `_validate`, `_edit_summary`,
  `_humanize`, `_node_type`, `_catalog`, `_needs_approval`, `_step_name`,
  `_truncate`) in one module, with public names (no leading underscore) since
  other modules import them.
- `_parse_json` in a small shared module: three unrelated services use it to
  read an AI reply, so it should not live in the studio.
- One module per job (list and detail, proposals, proposal testing, version
  history, run review). Either separate service classes that the routes call
  directly, or small classes composed by a thin `AutomationStudioService`.
  Pick one approach and use it throughout; do not mix.
- Break `run_detail` into named steps. It is the hardest method to read.
- Update every importer listed above. Do not leave re-export shims behind
  unless something outside this list needs them.

`services/new_workflow.py` and `services/chat_self_service.py` show the style
used in recent refactors: a module docstring that says what the module is for,
small methods, thin routes.

## Rules

- No behaviour change: same HTTP status codes and error messages, same response
  keys and values, same SQL results, same order of database writes, same AI
  prompt text (`PROPOSAL_SYSTEM` must stay byte-for-byte identical).
- Do not change route paths, methods or permissions in `studio.py`.
- Customer-service code must not import runtime internals. Use
  `app.runtime.validation` for `validate_workflow` (a contract test enforces
  this: `tests/runtime/contracts/test_runtime_public_boundary.py`).
- Do not edit existing tests to make them pass. Adding new tests is welcome.
- No new dependencies. No abstractions beyond what this split needs.
- Keep comments that explain why. Do not add comments that restate the code.
- Do not call the AI provider while checking your work (it costs money): do
  not run `create_proposal` with a typed request, `refine_proposal`,
  `test_proposal`, or `NewWorkflowService.draft_workflow`.
- Do not publish, restore, discard, flag or dismiss anything in the dev
  database. Read-only checks only.

## Safety net (do this before moving any code)

1. Add unit tests for the pure helpers, in a new file under
   `backend/tests/customer_service/`: `_validate` (a valid graph, a graph with
   an order-changing step and no approval before it, an unknown node type),
   `_graph_view`, `_diff`, `_edit_summary`, `_parse_json` (plain JSON, JSON in a
   code fence, text with no JSON), `_truncate`. Write them against the current
   code, see them pass, and keep them passing after the split (update only
   their import lines).
2. Write a throwaway script (do not commit it) that calls the read-only methods
   against the dev database and saves the JSON, so you can compare before and
   after. Dev workspace id: `14363957-27b0-49d0-ad88-4ee60476bc02`. Methods:
   `overview`, `workflow_detail` and `version_history` for each workflow in the
   overview, `node_library`, `review_queue`, `run_detail` for the first five
   runs in the review queue, and `get_proposal` for any workflow whose
   `open_proposal_id` is set. Use `app.core.session.get_db` for the session;
   run it from `backend/` with `PYTHONPATH=. .venv/bin/python script.py`.
   Sort keys and use `default=str` when dumping. The before and after files
   must be identical, apart from values that depend on the clock (for example
   "edited 3h ago" style fields, if any; name them in your report).

## Checks to run before and after (all from `backend/`)

```bash
uv run pytest -q
```

Expected before: 2439 passed, 0 failed (plus your new helper tests after step 1).

```bash
uv run ruff check app
```

Expected: "All checks passed!". Do not use `ruff --fix` blindly: in this
codebase it once removed an import that was still used.

```bash
uv run python -c "import app.main, app.platform.jobs.runner"
```

## How to work

- Create a new branch from `feature/cs-automation-live-desk` called
  `refactor/automation-studio`. Do not commit to the feature branch, do not
  push, do not merge.
- Read `frontend/docs/frontend/cs-next-session.md` first (sections 1, 3g
  and 3h).
- Postgres and Redis must be running for the tests. Never restart them.
- Two commits are fine: one for the new helper tests, one for the split.

## What to report back

- The new files, with line counts, and what each one holds.
- The longest method after the split, and its length.
- Which approach you chose (separate services or a composed one) and why.
- The results of the three checks, and the result of the before/after
  comparison, including any fields you had to ignore.
- Anything you noticed but deliberately left alone.
