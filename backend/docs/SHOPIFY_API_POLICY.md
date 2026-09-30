# Shopify Admin API policy

Tajeran Support OS V1 uses the Shopify **GraphQL Admin API only**, pinned to
`2026-07`. The application sends all live Shopify Admin requests to:

`https://{shop}.myshopify.com/admin/api/2026-07/graphql.json`

Production startup rejects a malformed or unapproved `SHOPIFY_API_VERSION` so
an outdated environment variable cannot silently fall forward to another API
version. Update the allow-list in `app/core/startup_validation.py` deliberately
during each quarterly Shopify API review, after GraphQL contract tests pass.

The current stable version is supported by Shopify until July 2027. REST Admin
API calls must not be added to product code; new public apps are GraphQL-only.
