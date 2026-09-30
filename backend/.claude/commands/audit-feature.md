Audit exactly one v1 feature and update its file in place. Argument: $ARGUMENTS (the feature slug, matching a file at .claude/features/<slug>.md).

Steps:

1. Read `.claude/features/<slug>.md`. If it doesn't exist, stop and say so —
   don't guess which feature was meant. Use `/log-feature` to create it first.
2. Read the "Spec" section only. Do not read any other feature file, and do
   not read `.claude/AUDIT_TRACKER.md` unless you need the layer boundary
   list from `.claude/CLAUDE.md`.
3. Based on "Layer" and "Likely location" in the spec, search ONLY the
   relevant part of the repo:
   - core → `app/runtime`, `app/tcos`, `agents_runtime`
   - product → `domains/customer_service`
   - provider → `providers/<name>`
   - cross-layer → search each of the above, but note in the result which
     layer each piece of the implementation actually lives in (and flag it
     if it crosses a boundary it shouldn't)
   Use grep/glob for symbol and filename matches before opening files. Don't
   read entire directories wholesale — open only files that matched a search.
4. For what you find, answer the three questions from CLAUDE.md: what
   exists, is it good enough, what's left. Be concrete — cite file paths and
   function/class names, not vague impressions.
5. Write the findings into that feature file's "Audit Result" and "Task
   List" sections, replacing what's there. Each task list item must be
   something an engineer or an agent could act on without re-reading this
   conversation — include the file path and the specific change.
6. Update the feature's row in `.claude/AUDIT_TRACKER.md` (status + owner
   if given).
7. Report back in the chat: a short summary (a few sentences), not a
   restatement of everything you just wrote to the file.

Do not start auditing a second feature in this same session, even if it
seems related — that's a separate `/audit-feature` run.
