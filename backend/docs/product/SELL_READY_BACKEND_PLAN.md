# Sell-Ready Backend Plan

Last audited: 2026-09-13. This audit describes the current working filesystem,
which includes a large uncommitted release increment. It does not describe only
the last Git commit.

## Product boundary

The first product to sell is an AI-native support operations backend for Shopify
stores with email and website chat. Its job is to understand a customer request,
recommend or execute safe work, expose the decision trail, and improve from
verified outcomes. Other social/channel adapters and generic platform expansion
are post-launch.

Status labels in this document:

- **Done:** implemented and covered by relevant local tests.
- **Partial:** meaningful implementation exists, but a safety, live integration,
  operational, or completeness gap remains.
- **Missing:** required launch behavior is not implemented.
- **Verify:** code exists, but production evidence is absent.

## Current measured baseline

- Alembic: one head, `cap046`.
- Test inventory: 686 test files, approximately 2,174 test functions; 262
  customer-service test files and approximately 715 customer-service tests.
- Focused run: `tests/customer_service/shopify`, `product`, and `commercial`:
  **136 passed, 1 warning**.
- Full run with `--maxfail=3`: **3 failed, 851 passed, 1 warning**.
  - `tests/cognitive/test_product_planning_public_boundary.py`: test reads the old
    `services/customer_support_product_planner.py` path after the implementation
    moved to `services/support/planning/`.
  - `tests/core/test_health_and_observability.py`: expects `cap041`; actual head is
    `cap046`.
  - `tests/customer_service/omnichannel/test_customer_service_omnichannel_provider_capabilities_api.py`:
    shared registry contains a test `ConcurrentProvider` without `capabilities()`.
- Static verification: `python -m compileall -q app` and Ruff fatal/error checks
  passed.

The focused result proves internal contracts against mocks/fakes. It does not
prove Shopify App Store compliance, a live Shopify development store, Resend DNS,
S3, ClamAV, multi-replica realtime, backups, or production deployment.

## Customer-service capability map

| Area | Stage | Evidence in current code | Work still required for paying stores |
|---|---|---|---|
| Product boundary | Done | `product.py`, P0/V1 frontend contracts | Keep hidden providers out; remove “sellable” wording until gate passes if it is exposed externally |
| Authentication and workspaces | Done/Verify | `app/authentication/`, `app/api/auth.py`, `app/api/workspaces.py`, `app/tenancy/`, `cap029-cap034` | Finish full-suite proof; review stale `docs/AUTH-TODO.md`; live cookie/CSRF/session/logout/password-reset/email-verification smoke tests |
| Tenant isolation/RBAC | Done/Verify | workspace principal, customer-service RBAC, cross-tenant tests | Add negative tests to every new route; audit any remaining `user_id` parameters that now carry workspace IDs |
| Inbox/core helpdesk | Done | conversations, messages, customers, tickets, notes, tags, macros, queues, teams, assignment, search, saved views | Load/concurrency test hot queries and add indexes from real query plans |
| Agent collaboration | Done | presence/leases, followers, mentions, notifications, collision/version handling | Multi-replica realtime transport and reconnect/ordering test |
| Helpdesk table stakes | Done | snooze, spam/phishing moderation, bulk actions, drafts, signatures, custom fields, productivity; `cap040-cap046` | Retention execution, scheduled-draft end-to-end delivery, attachment cleanup jobs, browser/API contract smoke |
| Email | Partial | verified Resend inbound boundary, identity service/routes, outbound service, idempotency tests | Provision real inbound domain/webhook/DNS; outbound SPF/DKIM/DMARC; bounce/complaint suppression; delivery reconciliation and live smoke |
| Website chat | Done/Verify | public widget settings/sessions/messages and orchestration path | Abuse controls/CAPTCHA decision, load test, reconnect/history/security browser smoke |
| Attachments/media | Partial | local/S3 abstraction, size/type checks, signed download, media worker/security/retry tests | Production image currently lacks `clamdscan`; deploy scanner sidecar/daemon, prove S3 lifecycle/retention, quarantine, signed URL, large-file and outage behavior |
| Knowledge | Done/Verify | inline/URL/file/Shopify sync, settings, citations/no-answer, eval APIs | Live crawl/PDF/Shopify sync quality set, stale-source refresh jobs, tenant/storage limits, prompt-injection/redaction evaluation |
| AI intelligence/replies | Done/Verify | structured multilingual intelligence, deterministic fallback, reply suggestions, quality | Golden evaluation set, hallucination/PII/prompt-injection thresholds, cost/latency SLO, model outage soak |
| Autopilot/approvals | Partial | conservative modes, decision explanation, durable waits and activity feed | Enforce one action/risk matrix at every entry point; prove no protected mutation bypass; kill switch and staged rollout |
| Workflow/runtime visibility | Done/Verify | jobs, retries/DLQ, waits, approvals, snapshots/replay, timeline, repair/learning | Load/soak, worker crash/recovery, queue lag alerts, replay side-effect proof in staging |
| SLA/routing/workforce | Done | calendars, policies, breach checks, escalation metadata, best-agent/capacity | Time-zone/DST/holiday production fixtures, concurrency/load test, notification delivery proof |
| Analytics/business value | Done/Verify | dashboard, workload, quality, productivity, business value | Definition review with product/finance, large-data performance, timezone and late-event correctness |
| Proactive playbooks | Done/Verify | six signals, durable incidents, cooldown and worker evaluation | False-positive thresholds, owner controls, notification live test, safe rollback |
| Billing/entitlements/quotas | Partial | plan catalog, Shopify checkout/sync/cancel, signed lifecycle boundary, enforced usage | Decide Shopify App Pricing vs manual Billing API; production mode, plan migration/upgrade/downgrade/grace/refund tests and authoritative reconciliation |
| Privacy/retention | Partial | consent, privacy requests, retention preview, Shopify webhook receipts | Actual export delivery and full mapped redaction/anonymization jobs, deadlines, legal-retention policy, PII-minimized receipts, deletion proof |
| Observability/operations | Partial | structured request logs, Sentry config, health/readiness, worker heartbeat, backup/restore scripts | Fix readiness test drift; dashboards/alerts, secrets provision, backup schedule, restore and incident drills |

## Shopify/provider capability map

| Capability | Stage | Current implementation | Required completion |
|---|---|---|---|
| Install initiation | Done | workspace owner/admin check, normalized shop, hashed 10-minute one-use state | Decide standalone vs embedded architecture and make install start on Shopify services only |
| OAuth callback | Partial | callback HMAC, state replay defense, code exchange, scope validation | For embedded: managed install/token exchange/session tokens. For standalone: retain authorization-code flow but add expiring offline token refresh |
| Scope handling | Blocked | configured scopes validated after exchange | Remove nonexistent `write_refunds`; minimize and declare scopes in Shopify configuration; obtain protected customer-data approval |
| Token storage | Partial | Fernet encryption and reauth flag | Production must reject plaintext/legacy writes; store refresh token/expiry; rotate keys/tokens; disable raw-token connect in production |
| Store connection | Partial | connect/read/test/update/delete; one active connection by convention | DB uniqueness/race protection, explicit one-store product policy, disconnect/reinstall semantics |
| Order lookup/context | Partial | exact name/ID lookup, cache, summary/context | Migrate REST calls to GraphQL; customer identity authorization; pagination/search; older-order product decision |
| Shipping status | Partial | derives prepared response from cached context | Fresh GraphQL fulfillment/tracking read and deterministic output contract |
| Refund | Partial | calculates refundable amount, scoped lines/restock, approval for real provider | GraphQL `refundCreate`, required operation idempotency, fresh pre/post state, partial/refund conflict/live tests |
| Cancel | Unsafe partial | provider guards fulfilled/already-cancelled | GraphQL `orderCancel`; approval parity; async/cancellable-job semantics; idempotency ledger |
| Address update | Unsafe partial | blocks fulfilled and updates shipping address | GraphQL order update; approval/policy parity; address validation; fresh-state race checks |
| Reship | Partial | creates tagged replacement draft order for review | GraphQL-only path, required approval/idempotency, product/variant/inventory validation and reconciliation |
| Damaged item | Contract gap | appears in nodes/templates | Canonical typed action is missing from service dispatcher; define behavior or remove promise |
| Action naming | Contract gap | `change_address` and `update_shipping_address` coexist | One enum/schema across HTTP, planner, template, manifest, node, service and provider |
| Mutation safety | Blocked | refund/reship approval; optional advisory-lock/audit-log dedupe | Protect cancel/address too; require idempotency; durable pending/succeeded/failed/unknown ledger with request hash and reconciliation |
| Compliance webhooks | Partial | HMAC, receipt dedupe, uninstall/token revocation, cache deletion | Declare mandatory topics in Shopify config; fast durable jobs; complete exports/redactions; do not store raw PII unnecessarily |
| Commerce webhooks | Missing | a normalizer exists, but live route rejects commerce topics | Subscribe order/refund/fulfillment/scopes topics; HMAC boundary; enqueue; ordering/dedupe; cache upsert/invalidate; periodic reconciliation |
| API technology/version | Blocked | mixed GraphQL and many REST Admin endpoints; configured `2026-01` | New public apps must be GraphQL-only. Move to current supported stable, add quarterly upgrade calendar and version-header monitoring |
| Billing | Partial/Decision | manual GraphQL `appSubscriptionCreate` path with test mode default | Prefer Shopify App Pricing for a new public app; otherwise explicitly certify legacy manual pricing. Never grant entitlement from client input |
| Live certification | Missing | broad mocked transport/unit/API tests | Development-store install/reinstall/reauth/webhook/actions/billing/privacy matrix with saved evidence |

## Prioritized execution plan

### S0 — Restore a trustworthy baseline (P0, first)

Tasks:

- Fix the three exact full-suite failures listed above without reverting the
  current refactor.
- Run the whole suite to discover failures after the first three; continue until
  green.
- Restore sanitized `.env.dev.example` and `.env.prod.example` from the actual
  `Settings` contract. Never include real credentials.
- Update stale `cap041` claims to `cap046` or derive the expected head rather than
  duplicating it in tests/docs.
- Update `docs/AUTH-TODO.md` and `docs/customer_service/backend-next.md` so completed
  capabilities are not described as missing.
- Decide whether the large working tree is one coherent release; split/commit only
  when the user asks.

Acceptance:

- `pytest -q`, Ruff, format check, compileall, migration checker and production
  Compose config all pass.
- A fresh developer can configure from sanitized examples and boot API + worker.
- Status docs name one migration head and one launch scope.

### S1 — Freeze Shopify product decisions and contracts (P0)

Tasks:

- Record whether the app is embedded or standalone. Embedded requires Shopify
  session-token authentication; standalone can keep authorization-code OAuth.
- Choose Shopify App Pricing (recommended for a new public app) or explicitly
  justify/manual-certify Billing API pricing.
- Define a typed action matrix for order read, shipping status, cancel, address
  change, refund, reship and damaged item: required scopes, allowed order states,
  risk, approval, idempotency, preconditions and verification.
- Decide one-store-per-workspace for v1 and enforce it in DB/API, or model multiple
  stores explicitly.
- Inventory protected customer data and request only scopes used by shipped paths.

Acceptance:

- One reviewed contract drives schemas, service, runtime manifest, planner nodes,
  workflow templates and frontend copy.
- No invalid `write_refunds` scope and no ambiguous action aliases remain.

### S2 — Shopify install, auth and secrets (P0)

Tasks:

- Add/link Shopify app configuration and declare access scopes plus mandatory
  compliance subscriptions there.
- Add expiring offline access-token fields and encrypted refresh flow with
  single-flight refresh and reauthorization fallback.
- Remove or production-gate `POST /shopify/connect` and its PATCH equivalent so a
  browser cannot install arbitrary raw tokens outside OAuth.
- Fail production when encrypted secrets cannot be written/read; plan key version
  and rotation. Never accept `plain:` tokens in production.
- Add install, replay, wrong-shop, reinstall, changed-scope, expired-token,
  concurrent-refresh and secret-redaction tests.

Acceptance:

- Real development-store install/reinstall succeeds using the selected auth model.
- Tokens never reach frontend/logs and refresh without merchant interruption.
- Requested/granted scopes exactly match shipped functionality.

### S3 — GraphQL-only Shopify provider (P0)

Tasks:

- Replace `/shop.json`, order lookup, refund calculation/create, cancel, address
  update, draft-order creation and webhook registration REST calls.
- Use Admin GraphQL global IDs and typed DTOs at the provider boundary; keep
  Shopify payload shapes out of domain logic.
- Handle `userErrors`, HTTP errors, GraphQL errors, cost/throttle extensions,
  `Retry-After`, timeouts and 401/403 reauthorization consistently.
- Pin a supported stable API version and capture the response version header;
  alert on fall-forward and schedule quarterly compatibility runs.

Acceptance:

- No production Shopify request uses `/admin/api/.../*.json`.
- Provider contract tests cover success, user error, throttle, timeout, malformed
  payload and reauth for every operation.
- All action scenarios pass against a development store.

### S4 — Durable webhooks, cache and reconciliation (P0)

Tasks:

- Subscribe mandatory privacy topics and app/uninstalled plus required
  order/refund/fulfillment/app-scope/billing lifecycle topics.
- Verify raw-body HMAC, validate shop/topic/ID, store a PII-minimized receipt, and
  return 2xx in under five seconds after durable enqueue.
- Process idempotently by shop/topic/webhook ID; handle duplicate and out-of-order
  events; retry transient failures and expose dead letters.
- Replace append-only permanent order cache with unique upsert, TTL/stale policy,
  webhook update/invalidation and forced fresh reads for mutations.
- Add periodic Shopify reconciliation because webhook delivery is not guaranteed.

Acceptance:

- Duplicate/out-of-order/crash-retry tests converge to correct state.
- Load test keeps acknowledgment under the provider deadline.
- A missed-webhook drill is repaired by reconciliation without duplicate actions.

### S5 — Mutation, customer identity and privacy safety (P0)

Tasks:

- Require a client/workflow idempotency key on every mutation and persist an
  operation before the provider call with workspace/shop/action/order/request hash,
  approval, attempts, result ID and pending/succeeded/failed/unknown status.
- Return the stored result for matching replay; return 409 for key/payload mismatch;
  reconcile unknown outcomes before retrying.
- Enforce the action matrix and resolved approval consistently in all entry points.
- Force a fresh precondition read and fresh postcondition verification.
- Bind inbound customer identity to Shopify customer/order data. An order number
  alone must never reveal PII or enable action; add secondary verification rules.
- Implement privacy request worker lifecycle: export package, merchant delivery,
  mapped customer/shop redaction or documented legal-retention anonymization,
  deadlines, evidence and receipt-payload minimization.

Acceptance:

- Cross-customer/order-guess tests reveal nothing and cannot mutate.
- Crash-at-every-boundary tests never double-refund/cancel/reship.
- Export and redact drills complete on representative linked records and prove the
  expected PII is gone.

### S6 — Customer-service production hardening (P0/P1)

Tasks:

- Certify Resend inbound signature/idempotency and outbound identity, DNS,
  bounce/complaint/suppression/retry/reconciliation flows.
- Provide S3 object lifecycle and a working ClamAV scanner deployment. The current
  production Dockerfile has no scanner despite production validation requiring
  `clamdscan`.
- Replace the process-local realtime hub with Redis Pub/Sub/Streams before more
  than one API replica; test tenant isolation, ordering and reconnect.
- Execute retention and attachment cleanup jobs; define legal holds.
- Set SLOs/alerts for API errors/latency, auth abuse, provider failure/throttle,
  worker lag/DLQ, webhook failure, LLM quota, backups and billing drift.
- Performance-test inbox/search/timeline/analytics, worker concurrency and DB pool.

Acceptance:

- Real email and website-chat journeys pass from inbound to resolution.
- Two API replicas deliver scoped realtime events correctly.
- S3/scanner/provider outages degrade safely and recover through durable jobs.

### S7 — Release and App Store certification (P0 exit gate)

Tasks:

- Build immutable image, migrate an empty DB, deploy isolated staging, seed a demo
  workspace and run API/worker health checks.
- Execute development-store matrix: install, scope update, token refresh, reinstall,
  old/recent order, tracking, partial refund, cancel, address, reship, duplicate
  submission, webhook duplicate/out-of-order, billing lifecycle, uninstall, data
  export and both redactions.
- Complete protected-customer-data and App Store review requirements; align listing
  promises with the product endpoint and actual behavior.
- Run encrypted backup, restore into a new database, failover and rollback drills;
  record RPO/RTO and the `cap034` forward-only rule.
- Perform security review: dependency/container scan, auth/RBAC/tenant test,
  SSRF/upload/webhook/replay/rate-limit/PII/log audit and secrets rotation drill.

Acceptance:

- CI and staging matrix are green with links/timestamps and no mocked substitutes.
- Alerts, support escalation, privacy response and rollback owners are named.
- Only then change release status from candidate to sell-ready.

## Post-launch backlog (not before P0)

- Rich returns/exchanges and reverse fulfillment.
- Additional production channels after each adapter meets the email/chat gate.
- Multi-store workspaces if merchant demand proves it.
- Advanced analytics, new proactive signals and broader generic-agent platform UX.
- Enterprise MFA/SSO and regional data residency based on target segment.

## Evidence log template

Append one entry when a stage materially changes:

```text
Date / stage:
Objective and acceptance criteria:
Files changed:
Migration:
Commands and exact results:
Live/staging evidence:
Security/privacy review:
Remaining risks:
Next command:
```

## External requirements used for this audit

Re-check these official sources when implementing because provider requirements
change:

- Shopify App Store requirements (GraphQL-only for new public apps, auth, billing):
  https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements
- Shopify GraphQL migration:
  https://shopify.dev/docs/apps/build/graphql/migrate
- Shopify API versioning:
  https://shopify.dev/docs/api/usage/versioning
- Shopify privacy/compliance webhooks:
  https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance
- Shopify webhook reliability:
  https://shopify.dev/docs/apps/build/webhooks
- Shopify app authentication and token exchange:
  https://shopify.dev/docs/apps/build/authentication-authorization/app-installation
- Shopify billing and App Pricing:
  https://shopify.dev/docs/apps/launch/billing
- Claude Code project memory, subagents and cost control:
  https://code.claude.com/docs/en/memory
  https://code.claude.com/docs/en/sub-agents
  https://code.claude.com/docs/en/costs

