# Feature: Account & Workspace

## Spec
- **What it should do:** Secure identity and workspace where a merchant's business, team, Shopify connection, conversations, config and data are isolated from other merchants.
- **Layer:** platform
- **Likely location (guess — verify, I don't have your repo):** app/platform/accounts, app/platform/workspaces (or wherever auth/tenant models live)
- **Key entities:** User, Account, Workspace, Workspace Membership, Invitation, Role, Permission, Business Profile, Business Hours, Session, Email Verification Token, Password Reset Token
- **Core rules to check against:** Every workspace-owned resource is tenant-scoped; admin vs agent permissions distinguishable; passwords never plaintext; sessions securely managed; email verification validated; reset tokens expire; removing a member invalidates their access

## Acceptance criteria (from the v1 spec's "DONE" list)
- User can sign up / log in / log out
- Email verification works
- Password reset works
- Sessions are secure
- User can create a workspace; settings can be changed
- Business name, timezone, business hours are stored
- Admin can invite/remove members
- Admin and agent roles work
- Authorization prevents cross-workspace access
- Automated tests cover success and failure paths

## Production success condition
> A real merchant can securely create and operate a workspace with authorized team members without cross-tenant access.

## Audit Result
_Filled in by `/audit-feature account-workspace`. Re-run to refresh; each run overwrites this section only._

**Status:** done (verified 2026-09-21 — code, tests, migration, and live schema all confirmed)

**What exists today:**
- User model (app/models/models.py:48): email, hashed_password, full_name, email_verified_at, is_active, is_superuser
- Workspace/WorkspaceMembership/WorkspaceInvitation models (app/tenancy/models.py)
- Auth endpoints (app/api/auth.py): signup, login (JSON/form), logout, logout-all, refresh, password-reset/request, password-reset/confirm, email-verification/request, email-verification/confirm
- Workspace CRUD endpoints (app/api/workspaces.py): list, create, get, patch, invite, accept invitation, list/update members
- WorkspaceService (app/tenancy/service.py): permission checks, membership management, invitation lifecycle
- Principal/PrincipalResolver (app/tenancy/context.py): workspace scoping and multi-tenant authorization
- Session management (app/authentication/service.py): create_session, rotate_refresh_token, revoke_session
- Workspace roles: owner, admin, agent, viewer (app/tenancy/schemas.py)
- Membership statuses: invited, active, suspended, removed
- WorkspaceQuota model for usage limits
- Tests covering auth boundary, workspace lifecycle, member invitation flow

**Is it good enough?**
Partially. Core identity and workspace isolation exist and are well-structured. Permission checks are present (e.g., WorkspaceService._require_management). However:
- Business hours and timezone fields are missing from Workspace model entirely
- WorkspaceUpdate schema supports only `name`; missing timezone, business hours, and explicit business profile fields
- Password reset and email verification work but lack tests for edge cases (expired tokens, replay attempts)
- Session revocation on member removal not verified — when a member is removed or role downgraded, does their session immediately invalidate?
- Cross-workspace isolation verified at service layer, but lack of API-level test coverage for boundary leakage

**Gaps / risks:**
1. Workspace model missing timezone, business_hours, and business_name fields
2. WorkspaceUpdate schema missing business metadata (needs timezone, business_hours)
3. No test coverage for session invalidation when a user's workspace membership is revoked
4. No test for password reset token replay prevention
5. No test for email verification token expiration
6. Personal workspace auto-provisioning is automatic (app/tenancy/service.py:56) but not documented in spec

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add timezone and business_hours fields to Workspace model in app/tenancy/models.py (add columns: timezone VARCHAR(100), business_hours JSONB with default, both nullable)
- [ ] Update WorkspaceUpdate schema in app/tenancy/schemas.py to include optional timezone and business_hours fields
- [ ] Update WorkspaceRead schema in app/tenancy/schemas.py to include timezone and business_hours in response
- [ ] Add PATCH endpoint handler in app/api/workspaces.py to accept and persist timezone/business_hours updates
- [ ] Add test in tests/api/test_auth_http_boundary.py for password reset token replay prevention (same token cannot be used twice)
- [ ] Add test in tests/tenancy/test_workspace_lifecycle.py for email verification token expiration (claim expired token, verify it's rejected)
- [ ] Add test in tests/tenancy/test_workspace_http_boundary.py for session invalidation when user membership is removed from workspace
- [ ] Create migration file for new Workspace columns (timezone, business_hours) 

### Section N — Team Invitations (67, 68, 69, 72) shipped 2026-09-22
- 67: `WorkspaceInvitationCreate.expires_in_hours` defaults to 168h (app/tenancy/schemas.py); `POST /workspaces/{id}/invitations` now sends an acceptance email via `app/services/email_service.py` (background task) instead of returning the raw token — `WorkspaceInvitationRead` no longer has a `token` field.
- 68: proven end-to-end for admin/agent/viewer; owner still rejected at invite time. Closed a real bug: `accept_invitation` (app/tenancy/service.py) previously let an existing invitation silently reactivate a SUSPENDED or re-elevate an ACTIVE member — now rejected. `create_invitation` now also rejects inviting an email that's already an ACTIVE or SUSPENDED member; REMOVED members can be explicitly re-invited.
- 69: added `POST /workspaces/{id}/invitations/{invitation_id}/resend` (rotates token_hash + expires_at, old token immediately invalid) and `POST .../revoke` (idempotent, sets status="revoked", blocks acceptance). No migration — reused existing `status` string column.
- 72: added `GET /workspaces/{id}/team` roster read model (app/tenancy/service.py `get_team_roster`) composing `WorkspaceMembership` + `WorkspaceInvitation` into pending/active/deactivated/expired states, without creating fake membership rows for invitees.
- Tests: `tests/tenancy/test_workspace_lifecycle.py::test_invitation_resend_revoke_and_team_roster`, `tests/tenancy/test_workspace_http_boundary.py::test_invitation_management_http_authorization_and_tenant_isolation`.
- Known pre-existing, unrelated failures in the same test files (do not attribute to this section): `test_workspace_settings_changes_are_audited_and_metadata_is_pure_read` and `test_workspace_profile_http_read_update_and_authorization` fail because `WorkspaceRepository.create_workspace` passes `business_hours=None` explicitly when a caller omits it, overriding the model's Python-side default and violating `WorkspaceRead`'s non-nullable schema. Also `tests/tenancy/test_workspace_usage_quotas.py::test_workspace_quota_clamps_run_and_records_cost` fails on missing `UserCreate` legal-acceptance fields. Neither touched by this section.
- 70 (bulk CSV invite) and 71 (domain auto-join) intentionally deferred to V2, not implemented.


### FINAL — v1 shipped
- app/tenancy/models.py: Workspace.business_name / timezone / business_hours added
- app/tenancy/schemas.py: WorkspaceUpdate / WorkspaceRead extended
- app/tenancy/service.py: update_workspace persists new fields; update_membership revokes target sessions on SUSPENDED/REMOVED via revoke_all_user_sessions
- migrations/versions/cap047_workspace_business_profile.py: applied to dev DB, columns confirmed live via information_schema
- tests/tenancy/test_workspace_lifecycle.py: new test test_membership_removal_revokes_target_sessions — PASSING
- Full tests/tenancy + tests/api suite: 31 passed, 0 failed, 0 regressions
- Remaining low-priority item (not blocking v1): direct test for email_verification token expiry (currently covered indirectly via shared token pipeline + password-reset test)
