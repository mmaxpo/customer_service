# Shopify privacy/compliance webhooks

The backend endpoint is:

`POST https://api-dev.tajeran.ai/customer-service/shopify/webhooks`

It verifies `X-Shopify-Hmac-SHA256` against the raw request body, requires a
Shopify webhook ID for idempotency, and accepts the three mandatory privacy
topics:

- `customers/data_request` — records a durable `pending_export` receipt.
- `customers/redact` — removes cached Shopify order data for the shop.
- `shop/redact` — removes cached order data and deactivates the shop connection.

`app/uninstalled` is also handled and revokes the stored Shopify token. Duplicate
deliveries return `202 {"status":"duplicate"}`.

The same endpoint now accepts the V1 commerce topics `orders/create`,
`orders/updated`, `orders/cancelled`, `fulfillments/create`, and `refunds/create`.
Verified order events update the workspace-scoped Shopify order cache and are
deduplicated by Shopify's webhook ID.

Shopify requires the mandatory topics to be declared as `compliance_topics` in
the app configuration, not registered as GraphQL `WebhookSubscriptionTopic`
values. The sanitized configuration is in
[`shopify.app.toml.example`](../shopify.app.toml.example).

Because this project is currently released from the Shopify Dev Dashboard,
apply the configuration there (or copy the example to `shopify.app.toml` and
run `shopify app deploy` after authenticating the CLI). The public URL must be
exactly the endpoint above, and the new app version must be released. Do not
send a real `shop/redact` test to the development store unless you intend to
deactivate and erase that installation.
