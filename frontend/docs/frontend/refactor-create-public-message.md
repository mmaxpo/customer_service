# Refactor task: split `create_public_message`

Give this whole file to the coding tool that will do the work.

## Goal

`create_public_message` in `backend/app/api/products/customer_service/channels.py`
(starts near line 341, about 230 lines) handles every message a customer sends
in the website chat. It is correct and covered by tests, but it is too long to
read or change safely. Split it into small, named steps **without changing what
it does**. This is a readability refactor, nothing else.

The owner cares most about readable code. A good result is a route function of
roughly 30 to 40 lines that reads like a list of steps, with each step in a
function whose name says what it does.

## What the function does today, in order

1. Loads the chat widget settings by public key; 404 if missing or disabled.
2. Loads the chat session; 404 if it does not belong to that widget's workspace.
3. If the request has a `client_message_id`: takes a lock, and if that message
   was already saved, returns the saved result with `idempotent_replay: True`.
4. Saves the customer's chat message and mirrors it into the inbox conversation.
5. Publishes a `customer.chat.message.created` event (not dispatched, not committed).
6. Decides who answers:
   - a team member already replied and the ticket is not resolved since → nobody
     automated (`dispatch_skip_reason = "team_member_is_handling"`);
   - otherwise the support orchestration service gets first go;
   - if it did not handle the message and the topic is cancellation or damaged
     product → a fixed "passed to our team" reply
     (`"risky_intent_requires_human_review"`);
   - otherwise matching workflows are enqueued.
7. Builds the response, saves it for idempotent retries when there is a
   `client_message_id`, commits through the chat service, and schedules
   conversation analysis in the background.

## Where the pieces should go

This file is an HTTP adapter. Two tests enforce that
(`backend/tests/api/test_customer_service_channels_http_boundary.py`):

- it must not import anything from `sqlalchemy` directly, and must not contain
  `db.commit(`, `db.execute(`, `db.flush(`, `db.add(`, `session.commit(`,
  `session.execute(`, `pg_advisory_xact_lock` or `hashtextextended(`;
- it must still contain the literal text `await service.commit()` and
  `acquire_public_ingress_lock(`.

So keep the commit call and the lock call in `channels.py`, and move decision
logic into a service. Suggested shape (adjust if you find something cleaner):

- A new service module under `backend/app/domains/customer_service/services/`
  for step 6 ("decide who answers"), returning the orchestration result and the
  `workflow_dispatch` dict.
- Small private helpers in `channels.py` for the idempotent replay (step 3) and
  for building the response payload (step 7).
- Reuse `_public_session(db, public_key, session_id)`, which already exists in
  the same file, for steps 1 and 2 if it fits without changing the 404 messages.

Look at `services/chat_self_service.py` for the style used in the last refactor
of this file: thin routes, a service class, a module docstring that says what
the module is for.

## Rules

- No behaviour change. Same status codes, same response keys, same skip
  reasons, same event payload, same order of database writes.
- Do not edit tests to make them pass. If a test fails, the refactor is wrong.
- Do not touch other routes in the file, and do not reformat unrelated code.
- No new dependencies, no new abstractions beyond what this split needs.
- Keep the existing comments that explain *why* (for example why risky topics
  go to a person). Do not add comments that only restate the code.
- The job worker runs workflow code, not this route, so no worker change is
  expected. If you find you need to change anything under `backend/app/runtime/`,
  stop and report instead.

## Checks to run before and after (all from `backend/`)

```bash
uv run pytest -q
```

Expected: 2439 passed, 0 failed (state at commit `dbab841e`).

```bash
uv run ruff check app
```

Expected: "All checks passed!". Do not use `ruff --fix` blindly: in this
codebase it once removed an import that was still used.

The tests that exercise this function most directly:

```bash
uv run pytest -q tests/customer_service/chat tests/api/test_customer_service_channels_http_boundary.py tests/customer_service/test_customer_service_route_registration.py
```

Also confirm the app still starts:

```bash
uv run python -c "import app.main, app.platform.jobs.runner"
```

## How to work

- Create a new branch from `feature/cs-automation-live-desk`; do not commit to
  that branch directly, and do not push without being asked.
- Read `frontend/docs/frontend/cs-next-session.md` first (sections 1 and 3g):
  it explains the environment and the traps already found.
- One commit, with a message that says what moved where.

## What to report back

- The new line count of `create_public_message` and of `channels.py`.
- Which functions or classes were created, and where.
- The output of the three checks above.
- Anything you noticed but deliberately left alone.
