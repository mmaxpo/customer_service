# Production checklist: `backend/.env.prod`

State on 2026-10-03. The file `backend/.env.prod` is not in git (it is ignored),
so secrets stay on your machine and on the server. Never paste a secret into a
chat, a commit or this file.

Production addresses used below:

- website and app: `https://tajeran.ai`
- backend: `https://api.tajeran.ai`

The app refuses to start in production when a setting marked **required** is
missing or wrong.

## Already done

- [x] `APP_ENV`, cookie and CSRF settings, rate limits
- [x] `RESEND_API_KEY` (production key)
- [x] `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET` (the new app "Tajeran Support")
- [x] `SHOPIFY_REDIRECT_URI`, `SHOPIFY_SCOPES`, `SHOPIFY_API_VERSION=2026-07`
- [x] `ATTACHMENT_SCAN_MODE=clamdscan`, `ATTACHMENT_STORAGE_BACKEND=s3`
- [x] `SHOPIFY_BILLING_TEST=false`

## 1. Random secrets (generate on your Mac, paste into the file)

Run each command, copy the output into the setting. Use a different value for
each one.

- [ ] `SECRET_KEY` (**required**, 32+ characters)

  ```bash
  openssl rand -hex 32
  ```

- [ ] `POSTGRES_PASSWORD` (letters and digits only, so it is safe inside an address)

  ```bash
  openssl rand -hex 24
  ```

- [ ] `BILLING_WEBHOOK_SECRET` (**required**, 32+ characters)

  ```bash
  openssl rand -hex 32
  ```

- [ ] `SHOPIFY_TOKEN_ENCRYPTION_KEY` (**required**)

  ```bash
  python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
  ```

- [ ] `TAJERAN_FIELD_ENCRYPTION_KEY` (**required**; run the same command again for a second, different value)

**Keep a copy of the two encryption keys in a password manager and never change
them.** They lock the Shopify access of every connected shop. If they are lost
or changed, every shop has to reconnect.

## 2. Database and Redis (run inside the same Docker setup)

Replace `PASSWORD` with the `POSTGRES_PASSWORD` from step 1. The host names
`postgres` and `redis` are the service names in `docker-compose.prod.yml`.

- [ ] `POSTGRES_USER=tajeran`
- [ ] `POSTGRES_DB=tajeran`
- [ ] `DATABASE_URL=postgresql+asyncpg://tajeran:PASSWORD@postgres:5432/tajeran`
- [ ] `LANGGRAPH_CHECKPOINT_DB_URL=postgresql://tajeran:PASSWORD@postgres:5432/tajeran`
- [ ] `REDIS_URL=redis://redis:6379/0` (**required**)

## 3. Addresses

- [x] `CORS_ALLOWED_ORIGINS=https://tajeran.ai`
- [x] `BILLING_SUCCESS_URL=https://tajeran.ai/app/billing?checkout=success` (the Billing page lives at `/app/billing`)
- [x] `BILLING_CANCEL_URL=https://tajeran.ai/app/billing?checkout=canceled`
- [x] `WEB_APP_URL=https://tajeran.ai` (used for the links in verification, password-reset and invitation emails)

## 4. AI

- [ ] `OPENAI_API_KEY`: create a separate key named "production" in the OpenAI dashboard, and set a monthly spending limit there.
- [ ] `OPENAI_MODEL=gpt-4.1-mini-2025-04-14` (the model development uses)
- [ ] `CS_INTELLIGENCE_MODEL`: leave empty, as in development.

## 5. File storage (DigitalOcean Spaces)

Attachments are stored in a Spaces bucket. In DigitalOcean: Spaces Object
Storage, create a bucket in the same region as the server (example: `fra1`),
with file listing set to private. Then API, Spaces Keys, generate a key.

- [ ] `S3_BUCKET` (**required**): the bucket name
- [ ] `S3_ENDPOINT_URL=https://fra1.digitaloceanspaces.com` (use your region)
- [ ] `S3_REGION=fra1` (today it says `us-east-1`)
- [ ] `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`: the Spaces key

## 6. Inbound email secret

- [ ] `INBOUND_EMAIL_WEBHOOK_SECRET` (**required**, must start with `whsec_`)

  The app will not start without it, even though we launch with chat only.
  In Resend: Webhooks, add an endpoint, and copy its signing secret. The
  endpoint address will be given when the server is up; a placeholder address
  is fine until then, because the secret is what the start-up check needs.

## 7. Can stay empty for launch

- `STRIPE_*` (five settings): no code uses them yet.
- `SENTRY_DSN`: error reporting; recommended soon after launch, not required.
- `TAVILY_API_KEY`, `BRAVE_API_KEY`, `BRIGHTDATA_API_KEY`, `GOOGLE_API_KEY`,
  `GOOGLE_CSE_ID`, `MCP_*`, `SEARXNG_URL`: web search providers. The production
  setup has no search service, and customer service does not need one.

## 8. After the file is complete

- [ ] Copy `.env.prod` to the server by a secure way (scp), never by email or chat.
- [ ] On the server it must sit at `backend/.env.prod`, readable only by you (`chmod 600`).

## Not part of this file, but needed before the first shop

- [ ] DigitalOcean server created (2 CPUs, 4 GB memory minimum; the virus scanner alone uses 1 to 1.5 GB).
- [ ] Cloudflare: `tajeran.ai` and `api.tajeran.ai` pointed at the server, HTTPS on.
- [ ] Feature branch merged into `main`.
- [ ] Decide plan prices: the website shows $29 / $79 / $199, the code charges $49 / $149 for Starter and Growth.
- [ ] Test emails to `support@tajeran.ai` and `sales@tajeran.ai` arrive.
- [ ] First shop's `myshopify.com` address, then choose Custom distribution on "Tajeran Support" and send the install link.
