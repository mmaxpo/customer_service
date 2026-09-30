# TCOS Customer Service — Frontend Handoff Spec

Sep 30, 2026 · @Mehdi Tajeran

## 1. Purpose and how to use this spec

This spec defines the customer-service experience for Tajeran (TCOS): what end customers see, what store admins see, and the nine screens that deliver it. Claude Code should **audit the existing backend first**, then build the frontend on top of what already exists.

How Claude Code should work through it:

1. Read sections 2–7 to understand the product model, data model and flows.
2. Run the capability audit in section 8 **read-only**. Record where each capability lives (module, endpoint, event) or that it is missing. Save findings in `.claude/features/` like the other audits.
3. For each gap, propose the smallest adapter or facade rather than rewriting core logic.
4. Build in the phases in section 10. Each phase should work end to end before the next starts.

Ground rules:

- **Respect layer separation.** The frontend and product layer talk to the core only through defined contracts (API or facade), never by importing runtime internals.
- **One source of truth.** Every screen reads the same run, step and version data. The customer view, the "How did I get this?" view and the admin orchestration view are three translations of one record.
- **Nothing risky happens silently.** Any action that changes money, orders or customer data goes through an approval gate and an idempotency key.

Design reference: the TCOS Orchestration Panel canvas (https://claude.ai/artifact/4DEXs9Z6LAft7cgSmKhvoz). Claude Code may not be able to open it, so section 7 describes every screen in enough detail to build without it.

## 2. Product model: two audiences, three levels

The same engine serves two very different people, so the UI shows the same run data at three levels of detail.

| Audience | What they want | What they see | What they never see |
| --- | --- | --- | --- |
| End customer (store's customer) | A correct answer, fast, and safety for anything involving money | Chat, a short progress card, the answer, "How did I get this?", confirmation cards, "Talk to a person" | Agents, tools, graphs, tokens, costs, versions |
| Store admin (workspace owner) | Control, trust, and a way to improve answers | Simple setup, workflows list, orchestration view, proposals, conversation review | Raw model chain-of-thought, other workspaces' data |

| Level | Who | Shows | Where |
| --- | --- | --- | --- |
| 1. Simple | Customer (default) | 3–4 plain steps while working, then the answer | Chat widget |
| 2. Details | Customer (one tap) | What was checked, sources, and any self-correction in one sentence | Under the answer |
| 3. Studio | Admin only | Full orchestration graph, reasoning summaries, tool calls, handoffs, timeline | Admin app |

**Vocabulary translation.** Each internal term has a customer wording and an admin wording. Never show the internal term to customers.

| Internal term | Customer sees | Admin sees |
| --- | --- | --- |
| Agent / node | (hidden, or a plain step like "Checking with the courier") | Step name, e.g. "Courier tracking" |
| Tool call / `capability.invoke` | "Checked your order" | Tool name, input, output, duration |
| Parallel agents | One grouped step, "Looking into it" | Separate nodes running side by side |
| Verifier revise loop | "I double-checked and corrected my first estimate" | Revise arrow with the issue found |
| Approval gate | "Needs your OK" card | Approval node plus the workspace rule that triggered it |
| Unmatched message | "Connecting you with our team" | "No match → your team" plus a suggestion to build a workflow |

## 3. Core concepts and data model

Everything belongs to a **workspace** (one per store owner). Workflows are versioned, and every run is pinned to the exact version it used, so any past conversation can be replayed and displayed correctly.

| Entity | What it is | Key fields the frontend needs |
| --- | --- | --- |
| Workspace | One store owner's tenant | id, name, connections, rules, members |
| Connection | A provider linked to the workspace (Shopify now, more later) | provider, status, capabilities it exposes |
| Capability | An action or lookup a step can use, e.g. `store.orders`, `courier.track`, `store.discounts` | key, name, description, side-effect level (read / write / money), required approval |
| Workflow | A saved way of handling one customer need, e.g. "Where is my order" | id, name, description, enabled, live\_version\_id, stats (chats, % solved) |
| Workflow version | An immutable spec of the workflow's graph | version number, status (draft / live / archived), spec (nodes, edges, node config), created\_by, created\_at, change summary |
| Workspace rules | Policies that apply to every workflow, e.g. "ask before refunds over X" | rule type, threshold, enabled |
| Router | Picks which workflow handles a message | chosen workflow, confidence, alternatives, unmatched flag |
| Conversation | The chat with one customer | channel, customer ref, status (open / waiting / handed over / closed), messages |
| Run | One execution of a workflow version for a message | id, conversation\_id, workflow\_version\_id, status, started/ended, overall verification result |
| Step (node run) | One node's execution inside a run | node\_id, type (agent / tool / logic / approval), status, input, output, tool calls, reasoning summary, customer\_label, timings, tokens |
| Handoff | Data passed from one step to another | from\_step, to\_step, short summary |
| Approval request | A paused action waiting for the customer or the admin | who approves, action, amount, target, status, idempotency key, expiry |
| Proposal | A suggested change to a workflow | base\_version\_id, patch, plain-language summary, diff (new / changed / removed nodes), test results, status |
| Test case | A past or example conversation used to check a draft | input messages, expected behaviour, last result |
| Suggestion | A cluster of unmatched messages that could become a workflow | topic, count, examples, drafted proposal id |
| Flag | An admin or customer marking an answer or step as wrong | run\_id, step\_id, note, source (admin / customer / low confidence) |

## 4. How saved workflows fit the TCOS core

Today the core creates a workflow for each message. The recommended model keeps that intelligence but makes the admin's saved workflow the **approved plan** the planner works inside.

1. **Router** reads the message and picks a saved workflow with a confidence score.
2. **Planner** turns the live version's spec into a concrete plan for this message (Planning IR → ExecutionGraph). It fills in parameters, like the order number, and may adapt within the workflow's allowed capabilities.
3. **Runtime** executes the graph. Every `capability.invoke` passes through workspace rules, approval gates and an idempotency key.
4. **Verifier** checks the draft answer and may send it back for revision. Its result (VerificationConfidence plus issues) is stored on the run.
5. **Answer** goes to the customer. The run is saved, pinned to the version it used.

Rules that keep this safe:

- The planner **may not use capabilities outside the version's allowed list**. If it adapts the plan, the step is marked "adapted" on the run so the admin can see it.
- **Unmatched messages** go to a human with a summary. The core may still draft a plan in the background ("shadow mode"), but only to seed a suggestion, never to answer the customer.
- The **learning capability produces suggestions and proposals only**. Nothing is published without an admin tapping Publish.
- **Workspace rules are enforced in the runtime**, not inside individual workflows, so editing a workflow can never remove a safety rule.

Open question for the audit: does the current planner accept a template or constraint input, or does it only plan from scratch? Section 8 asks Claude Code to check this first, because it decides how much adapter work is needed.

## 5. End-customer chat flow

The customer only ever sees a calm chat: a short progress card if the answer takes time, the answer, an optional explanation, and a confirmation card before any real action.

1. **Customer sends a message** through the chat widget or another channel.
2. **If the run takes longer than a short threshold** (default about 2 seconds, configurable per workspace), show a progress card titled "Looking into it for you" with 3–4 steps. Each step shows done (check), current (spinner) or next (empty circle). Fast answers skip the card.
3. **The answer appears** as a normal message, with the key fact in bold.
4. **"How did I get this?"** (if the admin enabled it) expands under the answer. It lists what was checked (e.g. order details, courier tracking, delivery policy) and, when the verifier corrected something, one plain sentence like "I double-checked the date and corrected my first estimate."
5. **If an action is needed** (refund, cancellation, address change), show a "Needs your OK" card with the action, amount, where money goes, and two buttons: "Yes, …" and "Not now". Include the line "Nothing happens until you tap yes." The run pauses on an approval request until the customer answers.
6. **Quick replies** under the answer, including "Talk to a person", which is always available.

Progress step labels:

- Each workflow node can carry an optional `customer_label` (e.g. "Checking with the courier"). Nodes without one are hidden from customers.
- Nodes that run in parallel are grouped into one customer step.
- The final "Writing your answer" step is always shown last.

Customer-visible states:

| State | What the customer sees |
| --- | --- |
| Working | Progress card with live step states |
| Answered | Answer, optional "How did I get this?", quick replies |
| Needs confirmation | "Needs your OK" card; composer stays usable |
| Confirmed | Short confirmation message, e.g. "Done. Your refund has been requested." |
| Handed over | "I'm connecting you with our team now" and a divider "Handed to our team" |
| Error or timeout | "I couldn't finish this. I'm connecting you with our team." Never a technical error message. |

## 6. Admin flows

The admin never uses a separate workflow builder. They manage workflows from a list, watch runs in the orchestration view, and change workflows by typing or by small edits on the same graph.

### 6.1 Workflows list

- Shows every workflow in the workspace as a card: name, status (Live vN / Draft / Suggested / System), one-line description, mini graph, chats in the last 7 days, % solved without a human, last edited.
- A routing strip at the top explains the model: Customer message → Router picks a workflow → N live workflows, or No match → your team.
- An "Ask TCOS" bar creates a new workflow or change from plain text and opens flow 6.3.
- Suggestion cards appear when unmatched messages cluster around a topic ("Customers asked about gift wrapping 18 times this week"). "Review draft" opens the drafted proposal in 6.3.
- "No match → your team" is a system workflow that cannot be deleted.

### 6.2 Orchestration view (live or past run)

- **Left:** the customer request and a "How it's thinking" timeline. Each item has a time, a step name and a one-line plain reason. Toggle between Summary and Full trace.
- **Center:** the run graph. Node states are done, running, queued, adapted and flagged. Dashed blue lines show handoffs between agents. Dashed amber lines show verifier revise loops. A run timeline below shows phases over time with a "now" marker.
- **Right:** an inspector for the selected node with tabs Trace, Input, Output and Config. Trace shows a reasoning summary, tool calls (name, input, output, duration) and handoffs in and out.
- Actions: Pause, Re-run this node, Edit node (opens 6.3 or 6.4 with that node selected).
- Reasoning shown here is a **stored short summary per step**, never raw model chain-of-thought.

### 6.3 Change by typing (proposal)

1. Admin types a request, e.g. "If a delivery is more than 2 days late, offer a 10% discount code."
2. The backend generates a **patch** against the live version and validates it against the workflow schema and the workspace's capabilities.
3. The graph shows the proposal in place: new nodes dashed amber with a NEW tag, changed nodes blue with CHANGED, removed nodes greyed out, unchanged nodes normal.
4. The left panel shows a plain summary with + (new), \~ (changed) and = (unchanged) lines, refine chips ("Only orders over \[AMOUNT\]") and a box for follow-up requests. Each refinement updates the same proposal.
5. The right panel shows a preview: test conversations replayed against the draft ("12 of 12 passed · 3 would now get a discount code") and a before/after answer with the added text highlighted.
6. Admin chooses Publish as vN+1, Save draft, or Discard. Publishing makes the new version live; any earlier version can be restored from version history.

### 6.4 Direct edit on the graph

- A "+" on each connection inserts a step there. Free wiring between arbitrary nodes is not allowed.
- The node library only offers capabilities from the workspace's connections, grouped as Agents, Tools and Logic (condition, loop, parallel, human approval).
- Selecting a node opens its settings: name, instructions, model, tools, inputs ("reads from"), guardrails such as max revision passes.
- The backend validates every edit and explains problems in plain words ("This refund step needs an approval before it").
- Direct edits produce the **same patch format** as typed changes and go through the same preview and publish.

### 6.5 Review a conversation and fix a step

1. Conversations enter "Needs review" when the admin flags an answer, the customer gives negative feedback, the run was handed over, or verification confidence was low.
2. The review screen shows the transcript (flagged message outlined), the run graph for that exact version, and a note tracing the problem to the likely step.
3. Selecting a step shows what it saw (raw input or tool output), what it did, and a "Fix this step" box with suggested chips and a prefilled rule.
4. "Propose fix" creates a proposal and opens 6.3. "Not a problem" clears the flag. "Take over chat" hands the live conversation to the admin.

### 6.6 Owner simple setup

- A friendlier home for non-technical owners. Skills (workflows) as on/off tiles, a "Change how it works" text box with suggestion chips and a Preview button, tone choice with a live sample reply, Safety & approvals switches (the workspace rules), and "Last change" with Undo.
- "Studio" in the side menu, labelled for advanced users, opens the workflows list and orchestration view.

## 7. Screen-by-screen spec

Nine screens cover both audiences. Numbers match the artboards on the design canvas.

| # | Screen | Audience | Layout and key components | Data it reads |
| --- | --- | --- | --- | --- |
| 1 | Orchestration view (live run) | Admin | Top bar (breadcrumb, run status, metrics, Pause, Edit). Left: request + thinking timeline. Center: run graph + legend + run timeline. Right: node inspector with tabs. | Run, steps, handoffs, live events |
| 2 | Edit mode | Admin (advanced) | Left: node library. Center: graph with "Ask TCOS" bar, ports, drop target, zoom. Right: node settings form with "Re-run from this node". | Version spec, capability catalog, draft state |
| 3 | In-chat summary | Admin (inside a chat or inbox) | Collapsed strip "Orchestrated 6 steps with 4 agents" + mini dots + "View orchestration" link, then the answer. | Run summary |
| 4 | Customer: working | Customer (mobile first) | Chat header, customer bubble, progress card with 3–4 step states, composer. | Customer-labelled steps, live events |
| 5 | Customer: answer and approval | Customer | Answer bubble, expandable "How did I get this?", "Needs your OK" card, quick replies incl. "Talk to a person". | Answer, evidence list, approval request |
| 6 | Owner simple setup | Admin (non-technical) | Side nav with Studio link. Skills tiles with switches. "Change how it works" box. Tone selector with sample. Safety switches. Last change + Undo. | Workflows (enabled), rules, tone, last proposal |
| 7 | Workflows list | Admin | Routing strip, "Ask TCOS" bar, suggestion card, grid of workflow cards incl. draft and system cards. | Workflows, stats, suggestions |
| 8 | Proposal on the graph | Admin | Left: request, change summary, refine chips, input. Center: graph with NEW / CHANGED marks. Right: test results, before/after, Publish / Save draft. | Proposal, diff, test results |
| 9 | Review and fix | Admin | Left: transcript with flagged message. Center: run graph with likely cause highlighted and a trace note. Right: step detail, "Fix this step" box, Propose fix. | Run, steps, flag, suggested cause |

Visual system:

- **Admin (screens 1–3, 7–9):** dark theme. Ground #0B0D10, panels #101216 / #15181E, borders #22262E. Text #ECEAE4, secondary #A3A7B0. Amber #F2A93B = running, new, needs attention. Blue #74A9FF = tools, handoffs, selected, changed. Teal #6FCFAE = done. Fonts Geist and Geist Mono.
- **Customer and owner setup (screens 4–6):** light warm theme. Ground #F7F4EE, cards #FFFFFF, borders #E6E1D6. Text #1E1D1A, secondary #5E5A52. Action blue #2F5BD3, success green #1F7A5C. Font Figtree, large rounded shapes.
- Status is never shown by colour alone: always pair colour with an icon or a word.
- Touch targets at least 44 px on customer screens.

## 8. Backend capability checklist

Claude Code checks each row read-only before building anything, fills in the Status column, and notes where the capability lives or what adapter is needed. Rows 3 and 4 go first, because they decide how much adapter work the rest needs.

| # | Capability | Needed for screens | What to look for | Status | Where it lives / gap |
| --- | --- | --- | --- | --- | --- |
| 1 | Workspace isolation on every query and event | All | Tenant id on runs, workflows, conversations; no cross-workspace reads |  |  |
| 2 | Workflow spec storage with versions (draft / live / archived) | 2, 6, 7, 8 | A stored graph spec per workflow, version numbers, one live version |  |  |
| 3 | Router: message → workflow + confidence + unmatched path | 1, 7, 9 | Intent or routing service in the customer-service product layer |  |  |
| 4 | Planner accepts a saved workflow as template or constraint | All runs | Planning IR / PlanCandidate input options; can it be limited to allowed capabilities? |  |  |
| 5 | Runs pinned to a workflow version | 1, 9 | workflow\_version\_id (or equivalent) on the run / ExecutionGraph record |  |  |
| 6 | Step records: input, output, tool calls, timings, tokens | 1, 9 | agents\_runtime / DAG engine persistence per node |  |  |
| 7 | Short reasoning summary per step (not raw chain-of-thought) | 1, 9 | A summary field written at step end, or a cheap summariser |  |  |
| 8 | Live run events stream | 1, 4 | Node started / finished, tool invoked, handoff, revise, approval events; SSE or WebSocket |  |  |
| 9 | Verifier result with confidence and issues | 1, 5, 9 | VerificationConfidence plus the list of issues and revise loops |  |  |
| 10 | Approval gates: pause, request, resume, expire | 5, 6 | Human Approval feature; run can wait on customer or admin |  |  |
| 11 | Idempotent side effects | 5 | `capability.invoke` with idempotency key, on-conflict-do-nothing |  |  |
| 12 | Evidence per answer for "How did I get this?" | 5 | Which capabilities and knowledge sources fed the answer |  |  |
| 13 | Customer-facing step labels and grouping | 4 | A customer\_label per node, or a mapping layer in the product |  |  |
| 14 | Handover to human with summary | 5, 9 | Inbox / Tickets / Routing-Teams integration |  |  |
| 15 | Natural language → workflow patch, with schema validation | 2, 6, 7, 8 | Workflow generation already exists; can it output a diff against a version? |  |  |
| 16 | Replay test conversations against a draft with side effects mocked | 8 | Dry-run mode in the runtime; stored test cases |  |  |
| 17 | Unmatched message clustering into suggestions | 7 | Analytics or AI Quality jobs over unmatched runs |  |  |
| 18 | Flags and feedback on runs and steps, with likely-cause hint | 9 | AI Quality / Outcomes feature |  |  |
| 19 | Workspace rules enforced in the runtime | 5, 6 | Policy check before capability.invoke; thresholds per workspace |  |  |
| 20 | Capability catalog per workspace from connections | 2, 8 | Shopify Actions exposed as named capabilities with side-effect level |  |  |

## 9. APIs and live events the frontend needs

These are the contracts the frontend needs, as suggestions. Claude Code should map each one to an existing endpoint or event first and only add a thin facade where nothing fits. All endpoints are scoped to the current workspace.

**Workflows and versions**

| Method and path (suggested) | Purpose |
| --- | --- |
| `GET /workflows` | List workflows with status, live version, 7-day stats |
| `GET /workflows/{id}/versions/{v}` | Full spec (nodes, edges, node config) for the graph |
| `PATCH /workflows/{id}` | Enable / disable, rename |
| `POST /workflows/{id}/versions/{v}/restore` | Make an earlier version live again (undo) |
| `GET /capabilities` | Node library: capabilities from the workspace's connections |
| `GET /rules` / `PUT /rules` | Workspace rules (approvals, handover, tone, "How did I get this?") |

**Proposals**

| Method and path (suggested) | Purpose |
| --- | --- |
| `POST /proposals` | Create from text (`{workflow_id?, request}`) or from a graph edit (`{workflow_id, patch}`); a missing workflow\_id means a new workflow |
| `POST /proposals/{id}/refine` | Add a follow-up request to the same proposal |
| `GET /proposals/{id}` | Summary lines, diff (new / changed / removed node ids), validation errors |
| `POST /proposals/{id}/test` | Replay test conversations against the draft, side effects mocked |
| `POST /proposals/{id}/publish` | Create version N+1 and make it live |
| `DELETE /proposals/{id}` | Discard |

**Conversations, runs and review**

| Method and path (suggested) | Purpose |
| --- | --- |
| `GET /conversations?status=needs_review` | Review queue |
| `GET /runs/{id}` | Run with steps, handoffs, verifier result, pinned version |
| `GET /runs/{id}/steps/{step_id}` | Step detail: input, output, tool calls, reasoning summary |
| `POST /runs/{id}/flags` | Flag an answer or step (`{step_id?, note}`) |
| `POST /runs/{id}/steps/{step_id}/rerun` | Re-run from a node (admin, sandboxed) |
| `POST /conversations/{id}/takeover` | Admin takes over the chat |
| `GET /suggestions` | Clusters of unmatched messages with drafted proposals |

**Customer chat**

| Method and path (suggested) | Purpose |
| --- | --- |
| `POST /chat/{conversation_id}/messages` | Customer sends a message; returns run id |
| `GET /chat/{conversation_id}/answers/{id}/evidence` | Data for "How did I get this?" |
| `POST /approvals/{id}/decision` | Customer or admin answers `approve` / `decline` |
| `POST /chat/{conversation_id}/handover` | "Talk to a person" |

**Live events** (one stream per run, SSE or WebSocket). Every event carries `run_id`, `workspace_id`, `ts`.

| Event | Payload | Used by |
| --- | --- | --- |
| `run.started` | workflow\_id, version, router confidence | 1, 4 |
| `step.started` | step\_id, node\_id, type, customer\_label | 1, 4 |
| `step.tool_called` | step\_id, capability, input summary | 1 |
| `step.completed` | step\_id, output summary, reasoning summary, duration, tokens | 1, 4 |
| `step.handoff` | from\_step, to\_step, summary | 1 |
| `verifier.revise` | issue, target\_step | 1, 5 (as one plain sentence) |
| `approval.requested` | approval\_id, action, amount, approver (customer / admin) | 5, 1 |
| `approval.resolved` | approval\_id, decision | 5, 1 |
| `run.answered` | message\_id, evidence ids | 4, 5 |
| `run.handed_over` | reason, summary | 5, 9 |
| `run.failed` | safe message for the customer, internal error for the admin | 4, 1 |

The customer stream sends only customer-safe fields (customer\_label, step state, answer, approval card). Tool inputs, reasoning summaries and internal errors go to the admin stream only.

## 10. Build order

Build in five phases. Each phase ships something usable and only depends on the phases before it.

1. **Phase 0 — Audit and contracts.** Complete the section 8 checklist. Write the API and event contracts from section 9 against what exists. Decide how saved workflows constrain the planner (section 4).
   - Done when: every row in section 8 has a status, and each gap has a proposed adapter.
2. **Phase 1 — Customer chat (screens 4, 5).** Progress card from live events, answer, "How did I get this?", approval card with idempotent execution, handover.
   - Done when: a real Shopify order question gets answered end to end, a refund cannot execute without the customer tapping yes, and a timeout hands over politely.
3. **Phase 2 — Read-only admin (screens 7, 1, 9 without Propose fix).** Workflows list, live and past orchestration view, review queue, flags.
   - Done when: the admin can open any conversation and see the exact graph, steps and version that produced the answer.
4. **Phase 3 — Change by typing (screen 8, and Propose fix on 9).** Proposals, diff on the graph, refine, test replay, publish, restore earlier version.
   - Done when: a typed change becomes a new live version only after passing test replay and an explicit Publish, and can be undone.
5. **Phase 4 — Direct edit, suggestions and simple setup (screens 2, 6, suggestion cards on 7).** Insert-on-edge editing, node settings, unmatched clusters, owner setup.
   - Done when: graph edits and typed edits produce the same patch format and pass the same validation.

Workspace rules (approvals, handover) are needed from Phase 1. The advanced edit screen (2) can wait until last, since most admins will change workflows by typing.

## 11. Prompt for Claude Code

Export this doc as Markdown, save it in the repo (for example `.claude/features/cs-frontend-spec.md`), then paste this prompt into Claude Code.

```
Read .claude/features/cs-frontend-spec.md fully. It describes the customer-service
frontend for Tajeran (TCOS): end-customer chat and the admin orchestration view.

Do NOT write code yet. Start with Phase 0:

1. Audit the backend READ-ONLY against every row in section 8
   ("Backend capability checklist"). Begin with rows 3 and 4
   (router, and whether the planner can use a saved workflow as a template
   or constraint).
2. For each row, record: status (Exists / Partial / Missing), the exact
   modules, classes, endpoints or events involved, and the smallest adapter
   needed for any gap. Save this to .claude/features/cs-frontend-audit.md.
3. Map every API and event in section 9 to an existing endpoint or event,
   or mark it as "new facade needed". Respect layer separation: the product
   layer and frontend must use contracts, never import runtime internals.
4. Stop and show me the audit summary and the proposed contracts.
   Wait for my approval before starting Phase 1.

Rules for all phases:
- Customers never see agents, tools, tokens, internal errors or raw
  reasoning. Use customer_label and the customer event stream only.
- Any action involving money, orders or customer data needs an approval
  gate and an idempotency key.
- Nothing publishes a new workflow version without an explicit admin Publish.
- Typed changes and graph edits must produce the same patch format.
```
