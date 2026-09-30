# Customer service P0 frontend contract

The first sellable promise is: **AI operations customer service for Shopify
stores, supporting email and website chat.** The frontend must not advertise
WhatsApp, Instagram, Facebook, or a generic omnichannel helpdesk.

## Launch surface

- `GET /customer-service/product` returns the stable product promise and sellable channels.
- `GET /customer-service/channels/` returns only `email` and `website_chat`.
- `GET /customer-service/omnichannel/providers/capabilities` returns only adapters explicitly marked production-ready.

## Shopify operations

Refund and reship are workflow-only real-store mutations. A direct call without
a resolved durable approval returns `409`.

- Refund requires `amount` and `scope.line_items[]` with `line_item_id`,
  `quantity`, and `restock_type` (`no_restock`, `cancel`, or `return`). Currency
  must match the order. Shopify calculates the maximum before the refund is sent.
- Reship requires `scope.replacement_line_item_id` and
  `scope.replacement_quantity`. It creates a tagged replacement **draft order**
  for merchant review; it does not create or claim a fulfillment.

## Merchant email sender

- `GET /customer-service/email/identity`
- `PUT /customer-service/email/identity` (owner/admin)
- `POST /customer-service/email/identity/verify` (owner/admin)

Production email replies are blocked until the merchant sender domain is
verified by Resend. Show `verification_status` and a reconnect/verify action.

## Workspace knowledge

- Sources: list, inline ingestion, URL crawl, PDF/text upload, Shopify sync,
  re-index, and delete under `/customer-service/knowledge/sources`.
- Settings: `GET|PUT /customer-service/knowledge/settings` controls citations,
  freshness, threshold, and `handoff`, `clarify`, or `draft_only` no-answer policy.
- Evaluations: list/create/run under `/customer-service/knowledge/evaluations`.
- Search responses include `answered`, `citations`, and no-answer policy/message.

All knowledge reads and writes are scoped to the authenticated workspace. The
legacy `/kb` routes now use that same workspace ID contract.

## Shopify billing

- `POST /customer-service/billing/shopify/checkout` with a server-known plan
  returns Shopify's merchant approval URL. A pending checkout grants no features.
- `POST /customer-service/billing/shopify/sync` verifies active subscriptions
  directly with Shopify and is the only path that activates paid entitlements.
- `GET /customer-service/subscription` is read-only billing state.
- `GET /customer-service/billing/shopify/portal` returns the Shopify Admin
  subscription-management URL.
- `DELETE /customer-service/billing/shopify/subscription` cancels through Shopify.

The frontend must never send or modify entitlements. It can select only
`starter`, `growth`, or `pro`; the backend owns prices and feature grants.
