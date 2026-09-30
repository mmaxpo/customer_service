# OpenCode model-routing setup

This repository uses OpenCode for decision work and bounded implementation while
keeping routine jobs on a cheaper model. Project configuration is in
`opencode.json`; agent definitions are in `.opencode/agents/`. OpenCode falls back
to the existing root `CLAUDE.md` because no `AGENTS.md` exists, so project rules
are shared without duplicating tokens.

## One-time credential setup

From the repository root, start OpenCode and connect each provider interactively:

```bash
opencode
```

Then run `/connect`, select **Anthropic**, and enter an Anthropic API key. Repeat
`/connect`, select **OpenAI**, and use the supported OpenAI login/API-key method.
Do not put either key in `opencode.json`, `.env.dev`, shell history, or Git.

After connecting:

```text
/models
```

Confirm these configured IDs are available:

- `anthropic/claude-sonnet-5`
- `openai/gpt-5.6-terra`
- `openai/gpt-5.6-luna`
- `openai/gpt-5.6-sol`

From a terminal, `opencode providers list` shows connected provider names and
`opencode models` shows available models. Credentials live in OpenCode's user data
directory, not this repository.

## Routing policy

| Agent | Model | Cost class | Use |
|---|---|---:|---|
| `decide` (default) | Claude Sonnet 5 | medium | Product/architecture decisions, plans, tradeoffs |
| `decide-openai` | GPT-5.6 Terra, high reasoning | medium | Independent OpenAI decision or alternative plan |
| `implement` | GPT-5.6 Terra, medium reasoning | medium | One approved vertical slice |
| `cheap` | GPT-5.6 Luna, low reasoning | very low | Mechanical edits, stale assertions, formatting, summaries |
| `@explore-cheap` | GPT-5.6 Luna | very low | Isolated, read-only repository search |
| `@review-claude` | Claude Sonnet 5 | medium | Read-only review after implementation |
| `@deep-review-openai` | GPT-5.6 Sol, high reasoning | high | Only critical auth/Shopify/privacy/irreversible decisions |

The default agent is read-only `decide`. Switch primary agents with Tab or start
one explicitly:

```bash
opencode --agent decide
opencode --agent decide-openai
opencode --agent implement
opencode --agent cheap
```

Recommended workflow:

1. Use `decide` for one stage and save a compact decision with acceptance criteria.
2. For a critical decision, ask `@deep-review-openai` to challenge it. Do not do
   this for routine changes.
3. Switch to `implement` and provide only the approved decision, active plan stage,
   and acceptance criteria.
4. Delegate broad search to `@explore-cheap`; keep edits in the primary session.
5. Use `@review-claude` on the final diff, then run narrow/full verification.
6. Start a new session for an unrelated stage. Check spend with `opencode stats`.

## Cost controls

- `small_model` is GPT-5.6 Luna for OpenCode's lightweight internal tasks.
- Automatic compaction and old-tool-output pruning are enabled.
- Subagent nesting is limited to one level.
- Session sharing and external-directory access are disabled.
- Large/noisy directories are excluded from the watcher.
- Decision and review agents cannot edit or run shell commands.
- Never ask two premium agents the same routine question. Use a second opinion only
  when a wrong decision costs more than the review.
- Give every task exact file boundaries and acceptance criteria. Use one sell-ready
  stage per session.

As of 2026-09-13, OpenAI lists Luna as its cost-sensitive model, Terra as the
balanced model, and Sol as the stronger professional-work model. Anthropic lists
Sonnet 5 as its speed/intelligence balance. Recheck IDs and pricing before future
changes:

- https://developers.openai.com/api/docs/models
- https://platform.claude.com/docs/en/models/overview
- https://opencode.ai/docs/agents
- https://opencode.ai/docs/providers
- https://opencode.ai/docs/rules

## Free OpenCode-hosted models

The local installation currently lists several `opencode/*-free` models. They are
not configured for this private backend because model quality, availability, and
data handling can differ. Use one manually only for non-sensitive disposable work
after reviewing the provider's current terms; do not use it for source containing
credentials, customer data, auth, billing, privacy, or Shopify mutations.

