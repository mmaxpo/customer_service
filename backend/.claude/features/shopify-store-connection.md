# Feature: Shopify Store Connection

## Spec
- **What it should do:** Securely connect a Shopify store to the correct workspace so Tajeran's Shopify capabilities can use it.
- **Layer:** provider
- **Likely location (guess — verify, I don't have your repo):** providers/shopify/oauth, providers/shopify/installation
- **Key entities:** Shopify Store, Shopify Installation, Shopify Connection, Shopify Credential, Integration, Webhook
- **Core rules to check against:** Connection belongs to exactly one workspace; credentials never exposed to frontend; OAuth state validated; store identity verified; required permissions checked; disconnect invalidates access; webhooks verified and tenant-scoped

## Acceptance criteria (from the v1 spec's "DONE" list)
- OAuth works; state is validated; store identity is verified
- Credential is encrypted; frontend never receives raw credential
- Correct workspace owns installation
- Connection status persisted; health can be checked
- Disconnect and reconnect work
- Tenant isolation enforced
- Tests cover success/failure

## Production success condition
> A real Shopify merchant can securely connect their store and Tajeran can perform an authenticated tenant-scoped Shopify operation.

## Audit Result
_Filled in by `/audit-feature shopify-store-connection`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**

**OAuth & State Management:**
- **ShopifyOAuthService** (`app/domains/customer_service/integrations/shopify/oauth.py`) — OAuth flow with methods: build_install_url(), verify_hmac(), exchange_code_for_access_token(), validate_granted_scopes()
- **ShopifyOAuthInstallSession** model — stores workspace_id, initiated_by_user_id, shop_domain, state_hash (SHA256 of plaintext state), expires_at (10 min), consumed_at (replay protection)
- **State creation** (`create_install_state()`) — generates 48-byte URL-safe random state, hashes it with SHA256, stores with 10-minute TTL
- **State consumption** (`consume_install_state()`) — retrieves state via hash, validates not expired/consumed, uses hmac.compare_digest for shop domain verification, marks consumed_at
- **HMAC verification** — uses hmac.compare_digest to prevent timing attacks; validates callback params against api_secret

**Connection & Credential Management:**
- **CustomerServiceShopifyConnection** model — id, user_id (indexed), workspace_id (FK to workspaces, indexed), shop_domain (indexed), access_token_encrypted (Text), status (String, default "active"), granted_scopes, installed_at, revoked_at, reauth_required_at
- **Credential encryption** — uses `app.core.security.secrets.encrypt_secret()` and `decrypt_secret()` to encrypt/decrypt access tokens in storage
- **Token not exposed to frontend** — connection schema (ShopifyConnectionRead) returns id, user_id, shop_domain, status, installed_at, revoked_at, reauth_required_at but NOT access_token_encrypted

**Workspace Isolation & Permissions:**
- **Workspace ownership** — CustomerServiceShopifyConnection has workspace_id FK to workspaces.id with CASCADE delete
- **OAuth session scoped** — ShopifyOAuthInstallSession includes workspace_id
- **Scope validation** — `validate_granted_scopes()` checks that all required scopes are present in response; raises error if any required scope missing
- **Shop domain validation** — uses regex SHOP_DOMAIN_PATTERN to validate format, hmac.compare_digest to verify consistency during callback

**Webhook & Disconnect:**
- **ShopifyWebhookReceipt** model — webhook_id (unique), shop_domain, topic, status, payload (JSONB), processed_at
- **Webhook HMAC verification** — `verify_webhook_hmac()` uses base64(HMAC-SHA256) validation via hmac.compare_digest
- **Disconnect support** — CustomerServiceShopifyConnection.revoked_at field (with mark_revoked() method implied)
- **Reconnect support** — reauth_required_at field to signal re-authentication needed (e.g., on 401 during API call)

**Tests:**
- OAuth HMAC validation (test_shopify_oauth_callback_validates_hmac)
- State validation (returns 400 on invalid state)
- Install URL construction (domain normalization)
- Scope presence validation

**Is it good enough?**
- **Mostly yes, but with gaps.** Core OAuth flow is secure; credentials are encrypted; state is protected.
  - ✓ OAuth works with state validation
  - ✓ HMAC verified with timing-attack-safe comparison
  - ✓ Store identity verified (shop_domain in state + callback)
  - ✓ Credentials encrypted at rest
  - ✓ Frontend never receives raw credential
  - ✓ Workspace owns installation (workspace_id FK)
  - ✓ Connection status persisted with installed_at/revoked_at
  - ✓ Disconnect via revoked_at field
  - ✓ Reconnect via reauth_required_at flag
  - ⚠️ **Tenant isolation:** Tested in OAuth callback but not comprehensively (no test for user from workspace A accessing workspace B's connection)
  - ⚠️ **Scope validation timing:** Happens AFTER token exchange (could fail after user already approved)
  - ⚠️ **Webhook scoping unclear:** ShopifyWebhookReceipt has shop_domain but no workspace_id; risk of cross-workspace confusion

**Gaps / risks:**
- **Tenant isolation not comprehensively tested:** OAuth callback checks workspace_id in state, but no test for: (1) user from workspace A trying to access workspace B's connection, (2) disconnect in workspace A not affecting workspace B. Risk: weak isolation boundary.
- **Order cache not workspace-scoped:** CustomerServiceShopifyOrderCache has user_id, shop_domain, order_id indexed but NO workspace_id. Risk: if two workspaces have same user, cache lookups could return wrong data.
- **Shipping tracking cache not workspace-scoped:** CustomerServiceShippingTrackingCache has user_id, provider, tracking_number indexed but NO workspace_id. Same risk.
- **Scope validation after token exchange:** `validate_granted_scopes()` is called on token_payload AFTER `exchange_code_for_access_token()` succeeds. If scopes missing, token is already obtained but validation fails. Suboptimal UX and wastes a token.
- **Webhook receipt not scoped:** ShopifyWebhookReceipt tracks webhook_id, shop_domain, topic but not workspace_id. If two workspaces are connected to same shop (edge case), webhook processing could get confused.
- **No explicit permission scope enforcement:** validate_granted_scopes() checks required scopes are present, but v1 spec mentions "required permissions checked." No evidence of explicit permission scope requirements validation beyond generic scopes list.
- **Disconnect doesn't invalidate API cache:** No evidence of cache invalidation when revoked_at is set. Risk: stale order/shipping data returned after disconnect.
- **Revoke/reauth endpoints unclear:** disconnect endpoint exists but unclear if it calls revoke on Shopify side (best practice to revoke token with Shopify immediately).
- **Connection health check incomplete:** test_shopify_connection endpoint exists but doesn't verify webhook subscription health (only tests order read).

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] **Tenant isolation audit:** Add test in `tests/customer_service/shopify/test_shopify_connection_tenant_isolation.py` that: (1) creates two users in different workspaces, (2) each connects a Shopify store via OAuth, (3) verifies each can only access their own connection, (4) verifies disconnect in workspace A doesn't affect workspace B.
- [ ] **Add workspace_id to caches:** Add `workspace_id: UUID` column to CustomerServiceShopifyOrderCache and CustomerServiceShippingTrackingCache in `app/domains/customer_service/models/shopify.py`. Update all inserts/queries to include workspace_id filter.
- [ ] **Scope validation earlier:** Move `validate_granted_scopes()` call to be computed from Shopify docs (before exchange) or cache the scope list before starting OAuth. Alternatively, fail immediately after exchange if scopes missing instead of returning partial error.
- [ ] **Webhook scope by workspace:** Add `workspace_id: UUID | None` column to ShopifyWebhookReceipt in `app/domains/customer_service/models/shopify.py`. Populate from connection.workspace_id during webhook processing. Add query filter to prevent cross-workspace leaks.
- [ ] **Explicit permission scope requirements:** Document required scopes (read_orders, write_orders, etc.) in ShopifyOAuthService.__init__ and add validation test `tests/customer_service/shopify/test_shopify_oauth_scope_requirements.py` that verifies error message on missing scope is actionable (tells user which scope Shopify rejected).
- [ ] **Cache invalidation on disconnect:** Add method `invalidate_shopify_caches(workspace_id, shop_domain)` in `app/domains/customer_service/services/shopify.py` that deletes CustomerServiceShopifyOrderCache and CustomerServiceShippingTrackingCache rows for that workspace/shop. Call from delete_connection().
- [ ] **Explicit Shopify token revoke:** Add step in `ShopifyService.delete_connection()` to call Shopify GraphQL/REST API to revoke the access token before marking revoked_at. Wrap in try/except to not fail local disconnect if Shopify unreachable.
- [ ] **Webhook subscription health check:** Add method `verify_webhook_subscriptions()` to ShopifyService that: (1) queries Shopify for active webhooks, (2) validates compliance topics are registered, (3) returns status + missing topics. Call from test_connection() endpoint.
- [ ] **Disconnect validation test:** Add test `test_shopify_disconnect_invalidates_access()` that: (1) connects a store, (2) performs an operation (e.g., get order), (3) disconnects, (4) attempts another operation, (5) verifies 401 or "no connection" error (not cached stale data). 
