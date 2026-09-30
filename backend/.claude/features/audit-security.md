# Feature: Audit & Security

## Spec
- **What it should do:** All sensitive operations are authorized, tenant-isolated, securely stored, and auditable across the whole product.
- **Layer:** platform
- **Likely location (guess — verify, I don't have your repo):** app/platform/security, app/platform/audit (cross-cutting authn/authz/audit-log)
- **Key entities:** Audit event (login, config change, AI action, human action, Shopify action, approval, workflow execution, membership change, integration change)
- **Core rules to check against:** Every workspace resource tenant-scoped; authorization enforced server-side; credentials encrypted; Shopify tokens protected; webhooks verified; sessions secured; secrets never logged; audit records cannot be silently modified/deleted by ordinary users

## Acceptance criteria (from the v1 spec's "DONE" list)
- Tenant isolation enforced; authorization server-side; admin/agent permissions work
- Credentials and Shopify tokens secure; webhooks verified; sessions secure
- No sensitive data in logs; important actions audited
- Security and cross-tenant tests exist

## Production success condition
> A merchant's customer, commerce, AI, and operational data remains isolated and important actions can be traced to an authorized actor.

## Audit Result
_Filled in by `/audit-feature audit-security`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- CustomerServiceAuditLog model (app/domains/customer_service/models/tickets.py) with fields: id, user_id, actor_id, entity_type, entity_id, action, message, meta, created_at
- AuditLogRepository (app/domains/customer_service/repositories/audit_logs.py) and AuditLogService (app/domains/customer_service/services/audit_logs.py)
- API endpoint GET /customer-service/audit-logs (app/api/products/customer_service/analytics.py) with permission check cs.audit.read
- RBAC system (app/domains/customer_service/security/rbac.py) with roles: owner, admin, agent, viewer; and permission-based access control
- Shopify token encryption (app/core/security/secrets.py) using Fernet encryption with env-based keys
- Webhook HMAC verification for Shopify (app/domains/customer_service/integrations/shopify/lifecycle.py) using hmac.compare_digest
- Session management (app/authentication/service.py) with session creation, rotation, and revocation
- Password hashing via hash_password and verify_password (app/identity.py)
- Credentials stored encrypted (access_token_encrypted field in ShopifyConnection model)

**Is it good enough?**
Partially. Core security mechanisms exist (encryption, RBAC, session management, webhook verification), but there are critical audit and tenant isolation gaps:
- **CRITICAL TENANT ISOLATION BUG**: CustomerServiceAuditLog lacks workspace_id field. AuditLogRepository.list() filters only by user_id (app/domains/customer_service/repositories/audit_logs.py:49), not workspace. A user can query audit logs for any user if they know the user_id.
- Audit logs are only in product layer (customer_service), missing platform-level events (logins, membership changes, workspace settings, integrations)
- No audit log immutability protection — database admins can modify/delete audit records silently
- No detection/masking of secrets in logs (tokens, passwords could be logged if passed via logs)
- No audit retention policy or archival
- RBAC focuses on customer_service permissions but doesn't block cross-workspace access at the audit level

**Gaps / risks:**
1. **CRITICAL**: CustomerServiceAuditLog missing workspace_id field causes tenant isolation failure
2. **CRITICAL**: AuditLogRepository.list() filters by user_id only, enabling cross-workspace audit log leakage
3. Audit logs confined to product layer; platform-level events (login, logout, workspace member add/remove, API key generation, Shopify token rotation) not logged
4. No audit immutability (write-once storage or append-only log) — audit records are mutable by admins
5. No secret detection/masking in logs (could contain tokens, passwords, API keys if logged)
6. No tests for cross-workspace audit log isolation (can user A in workspace 1 see audit logs for user B in workspace 2?)
7. No test verifying secrets are not logged in audit trail or error messages
8. Audit log endpoint GET /audit-logs requires cs.audit.read but doesn't enforce workspace_id filtering
9. No audit retention policy; logs could grow unbounded
10. No API to delete/archive audit logs; immutability is not enforced

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] **CRITICAL**: Add workspace_id field to CustomerServiceAuditLog model (app/domains/customer_service/models/tickets.py) and add ForeignKey("workspaces.id", ondelete="CASCADE")
- [ ] **CRITICAL**: Update AuditLogRepository.list() in app/domains/customer_service/repositories/audit_logs.py to filter by workspace_id in addition to user_id
- [ ] **CRITICAL**: Update AuditLogService.list_logs() to accept and pass workspace_id parameter
- [ ] **CRITICAL**: Update list_audit_logs() endpoint in app/api/products/customer_service/analytics.py to pass workspace_id from current_user.workspace_id to service
- [ ] Create platform-level audit logging service (app/platform/audit/service.py) to capture: login, logout, password-reset, email-verification, workspace-create, member-invite, member-remove, role-change, Shopify-token-rotation, API-key-create/revoke
- [ ] Add platform audit log model (app/platform/audit/models.py) with fields: id, workspace_id, user_id, actor_id, action, entity_type, entity_id, payload, ip_address, user_agent, created_at
- [ ] Create migration for CustomerServiceAuditLog to add workspace_id column (non-nullable, backfill for existing rows to workspace of user)
- [ ] Add test in tests/customer_service/test_audit_isolation.py: user in workspace A cannot list audit logs from workspace B via same user_id
- [ ] Add test in tests/api/test_audit_log_no_secrets.py to ensure password hashes, tokens, API keys never appear in audit message/meta fields
- [ ] Add test for login/logout events appear in platform audit log within app/platform/audit table 
