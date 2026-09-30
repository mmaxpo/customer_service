# Test Risk Matrix

| Concept | What to Prove | Search Keywords | Status |
|---|---|---|---|
| Security / Ownership | User B cannot access User A data | ownership, user_scoped, cannot access, 404 | Track |
| Idempotency | Duplicate event creates only one result | duplicate, idempotent, idempotency | Track |
| Concurrency | Parallel requests do not lose/duplicate work | concurrent, gather, parallel | Track |
| Failure / Retry / DLQ | Failed job retries then dead-letters | dead_letter, retry, failed, failure | Track |
| Validation Errors | Invalid input returns 422 | 422, invalid, validation | Track |
| Empty State | Empty list returns [] not crash | empty, [] | Track |
| Permission Denied | Unauthorized/forbidden is blocked | permission, forbidden, 401, 403 | Track |
| Duplicate Events | Same webhook/message handled once | duplicate event, duplicate webhook | Track |
| Unavailable Agent | Offline/busy agent is not selected | offline, busy, unavailable, availability | Track |
| Over-capacity Agent | Full agent is not selected | capacity, max_open, workload | Track |
| Workflow Pause/Resume | Paused workflow resumes correctly | pause, resume, approval, wait | Track |
| External API Failure | Shopify/API failure returns safe result | shopify error, external failure, api failure | Track |
