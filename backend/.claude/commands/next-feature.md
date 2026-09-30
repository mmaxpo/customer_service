Start-of-session entry point. This is how every audit session should begin
— don't jump straight into `/audit-feature <slug>` unless the person already
told you the slug in their message.

Steps:

1. Read `.claude/AUDIT_TRACKER.md` only (not the feature files themselves —
   that's the whole point, this step is nearly free).
2. List the features that are `not-started` or `in-progress`, grouped by
   layer, with their status. Don't list `done` features unless asked.
3. Ask the person which one to work on next. If $ARGUMENTS already names a
   feature or slug, confirm it against the tracker instead of asking.
4. Once a feature is chosen, run the same steps as `/audit-feature <slug>`
   for it (read that one feature file, search only its layer, write the
   result back, update the tracker row).

Never read more than one feature file in this command. If the person wants
to compare two features before choosing, tell them that's better done as a
question about the tracker table you already printed, not by opening both
files.
