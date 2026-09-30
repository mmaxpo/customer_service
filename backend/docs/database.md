# Database Architecture & Connection Management

This document describes how PostgreSQL connections, pooling, and scalability
are handled in the backend.

---

## App-Level Pooling (SQLAlchemy)

Configured in `app/core/session.py`:

- `pool_size = 5`
- `max_overflow = 5`
- `pool_timeout = 30`
- `pool_pre_ping = true`

### Purpose

- Prevents too many open connections
- Protects PostgreSQL from overload
- Improves stability under load
- Works well for small/medium traffic

This setup is sufficient for MVP and early production.

---

## Most important runtime tables:
```text
workflow_runs
  stores workflow JSON + current state + status

workflow_run_events
  stores node_start, node_end, run_paused, run_end, errors
```



## TODO: Enable PgBouncer (Scaling Phase)

When traffic increases, enable PgBouncer in DigitalOcean Managed PostgreSQL.

PgBouncer provides server-side connection pooling and reduces pressure
on the main database server.

---

## Split Database URLs (Future Setup)

After enabling PgBouncer, split database URLs:

```env
# Direct connection (migrations / admin)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Pooled connection (application runtime)
DATABASE_URL_POOLED=postgresql+asyncpg://user:pass@pgbouncer-host:6432/dbname
```

## Usage Rules
- FastAPI App:
  - DATABASE_URL_POOLED
- Alembic:
    - DATABASE_URL

### Reason for URL Separation
- PgBouncer improves scalability
- Alembic requires session-level connections
- Transaction pooling can break migrations
- Prevents schema corruption
- Avoids connection state issues

### TODO: Future Improvements

- **Planned enhancements**:
	-	Enable PgBouncer in DigitalOcean panel
	-	Switch app to DATABASE_URL_POOLED
	-	Keep Alembic on direct DATABASE_URL
	-	Monitor active connections
	-	Tune pool sizes per environment
	-	Add metrics and alerts
	-	Consider read replicas (if needed)


- **Best Practices**:
	-	Keep pool sizes small per instance
	-	Scale horizontally instead of opening many connections
	-	Never run migrations through PgBouncer
	-	Store DB credentials in secrets manager
	-	Rotate credentials periodically
	-	Use different credentials per environment
	-	Restrict production DB access