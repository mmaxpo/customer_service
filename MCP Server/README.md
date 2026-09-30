# Tajeran.ai MCP Server

This repository contains the **MCP (Model Context Protocol) Server** for Tajeran.ai.

It provides external tools (Search, Web Extraction, Knowledge, CRM, etc.) that are used
by the main backend and AI agents.

The backend acts as an orchestrator.
All heavy integrations and external services live here.

---

## 🏗 Architecture

- Backend: Workflow engine, agents, orchestration
- MCP Server: Tools, providers, integrations
- Providers: Actual implementations (HTTP, APIs, browsers, etc.)

---

## ✅ Current Tools

### 🔍 Search
- Providers: SearxNG, Brave, Tavily, BrightData
- Endpoint: `/mcp/search`

### 🌐 Web Extract
- Provider: SimpleHttpProvider (HTML fetch + strip)
- Endpoint: `/mcp/extract`

### 📚 Knowledge
- Embedding + Retrieval Services

### 📩 Email / CRM / Files / Payments
- Modular provider architecture

---

## 📌 Web Extraction Status

Currently implemented:

- Simple HTTP fetch
- Basic HTML stripping
- Title extraction
- Caching
- Rate limiting

Limitations:

- No JavaScript rendering
- Limited support for modern websites
- Not reliable for Shopify / SPA / React apps

---

## 🚧 TODO: Real Shopify & Dynamic Website Extraction (High Priority)

This is critical for Tajeran.ai.

We will implement **Playwright-based extraction** to support modern websites.

### Planned: PlaywrightProvider

Features:

- Full JavaScript rendering
- Headless Chromium
- Screenshot / DOM access
- Scroll & wait strategies
- Anti-bot handling (basic)

### Supported Use Cases

With Playwright, we want to support:

- ✅ Product pages
- ✅ Cart pages
- ✅ Help centers
- ✅ Policies
- ✅ Reviews
- ✅ Dynamic pricing
- ✅ Metafields rendered by JS
- ✅ Shopify themes
- ✅ Headless storefronts

---

## 📋 Implementation Roadmap

### Phase 1 (Done)
- [x] Simple HTTP provider
- [x] Router
- [x] Caching
- [x] Rate limiting
- [x] MCP integration

### Phase 2 (Next)
- [ ] Readability / Article parser provider
- [ ] Better content cleaning
- [ ] Boilerplate removal

### Phase 3 (High Priority)
- [ ] PlaywrightProvider
- [ ] Browser pool
- [ ] Timeout management
- [ ] Resource cleanup
- [ ] Docker browser support
- [ ] Fallback strategy

### Phase 4 (Advanced)
- [ ] Proxy rotation
- [ ] CAPTCHA detection
- [ ] Stealth mode
- [ ] Session persistence
- [ ] Cookie management

---

## ⚙ Development

### Run Locally

```bash
uv run uvicorn app.main:app --reload --port 8001


---

## ✅ Why This Is Good For You

This README:

✔ Shows clear technical vision  
✔ Documents roadmap  
✔ Makes repo “investor-ready”  
✔ Helps future contributors  
✔ Keeps you focused on monetizable features  

---

## 🔜 Next Step (Recommended)

After this, the best move is:

> Build **PlaywrightProvider skeleton (no browsers yet)**

So later you just “plug in” Chromium.

If you want, I’ll give you that skeleton next.