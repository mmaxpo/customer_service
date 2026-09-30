# Release 1 production runbook

## Release sequence

1. Build one immutable image with `docker build -f infra/Dockerfile .`.
2. Create and verify a PostgreSQL custom-format backup.
3. Run `alembic upgrade head` as a one-off release job. Do not start API or
   worker replicas until it succeeds.
4. Start workers, then API replicas. Readiness requires both PostgreSQL and the
   exact Alembic head; liveness only proves the process is responsive.
5. Verify `/health/ready`, one authenticated workspace request, one agent run,
   usage-ledger recording, Shopify webhook verification, and worker job pickup.

## Environment contracts

Only `.env.dev` and `.env.prod` are supported, and both remain gitignored because
they may contain secrets. Local commands load `.env.dev` by default. Production
and staging commands must set `APP_ENV=production` or `APP_ENV=staging`; Compose
injects `.env.prod` explicitly. Tests load neither file when `APP_ENV=testing`.
Provision both files through the developer bootstrap or deployment secret manager
after a fresh clone; do not recreate a generic `.env` file.

Pytest never uses the development database. At session bootstrap it creates a
unique `tajeran_pytest_*` PostgreSQL database, migrates it to head, removes any
inherited provider credentials in favor of inert non-routable test values, and
drops the database when the suite finishes.
`APP_ENV=production` and `APP_ENV=staging` are rejected by this bootstrap guard.

## LLM provider degradation

OpenAI SDK retries are disabled in favor of classified application retries.
Temporary 429/5xx/network failures receive bounded jittered backoff and feed a
process circuit breaker plus structured resilience counters/logs. Quota/billing
429s are non-retryable and open the circuit immediately. Durable workflow jobs
retry provider failures at the job boundary; configured customer-chat workflows
emit a human-review fallback only on the terminal attempt. Alert on
`llm_provider_retries_exhausted`, `llm_quota_exceeded`, and circuit-open events.

## Migration and rollback policy

There is exactly one supported path from an empty database to `head`. CI creates
a clean PostgreSQL database, applies every migration, and runs the full suite.
Never use Alembic stamp to skip migrations in a release.

Schema-only revisions may provide a tested downgrade. `cap034` is an ownership
cutover and is deliberately forward-only because mapping organization data back
to one user would corrupt tenant ownership. After `cap034`, rollback means:

1. stop writes and workers;
2. redeploy the prior application image only with its matching pre-migration
   database backup;
3. restore into a new database, validate it, then switch traffic;
4. retain the failed database for investigation.

Never run an in-place downgrade through `cap034`.

## Backups and recovery drills

- Run `scripts/backup_postgres.sh` on a schedule, encrypt the resulting dump,
  copy it to versioned off-site object storage, and enforce retention.
- Alert when a backup is missing or fails `pg_restore --list` validation.
- At least monthly, restore the newest dump with `scripts/restore_drill.sh` into
  an isolated database whose name ends in `_drill`.
- During the drill, apply pending migrations, start an isolated API/worker pair,
  verify readiness and representative merchant records, and record RPO/RTO.

## Observability and incidents

Logs are JSON and include request ID, status, duration, route, and workspace ID
when supplied. Propagate `X-Request-ID` through proxies and workers. Configure
`SENTRY_DSN` for exception monitoring and trace sampling; never enable default
PII collection. Alert on readiness failures, 5xx rate, auth abuse/429s, quota
rejections, job dead letters, worker lag, Shopify reauthorization, and database
capacity.

## Shopify and privacy operations

Configure the four mandatory topics: `app/uninstalled`,
`customers/data_request`, `customers/redact`, and `shop/redact`. Data requests
are durably recorded as `pending_export`; operations must deliver the export to
the merchant within the provider deadline and mark the case complete. Redaction
and uninstall handlers are idempotent and remove credentials/cache data.
