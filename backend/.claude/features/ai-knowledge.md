# Feature: AI Knowledge

## Spec
- **What it should do:** Merchant-specific knowledge (FAQ, policy, product info, URL, custom text) that Tajeran retrieves and uses when answering customer questions.
- **Layer:** core (retrieval) + product (source management UI)
- **Likely location (guess — verify, I don't have your repo):** app/tcos knowledge/retrieval + domains/customer_service knowledge source management
- **Key entities:** Knowledge Source, Knowledge Document, Knowledge Chunk, Knowledge Version, Knowledge Metadata, Embedding
- **Core rules to check against:** Knowledge belongs to workspace; deleted knowledge no longer retrieved; retrieval tenant-scoped; source changes reflected in searchable knowledge; AI distinguishes retrieved knowledge from assumptions

## Acceptance criteria (from the v1 spec's "DONE" list)
- All v1 source types can be added/edited/deleted
- Search works; relevant knowledge retrievable; AI can use it
- Deleted knowledge is not retrieved; tenant isolation works
- Tests cover ingestion and retrieval

## Production success condition
> A merchant can provide their own knowledge and Tajeran reliably uses it when handling customer questions.

## Audit Result
_Filled in by `/audit-feature ai-knowledge`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- **Core retrieval layer** (`app/services/knowledge_*.py`): Text chunking (900-char chunks, 120-char overlap), embedding via `embed_texts()`, hybrid search combining FTS and vector similarity, user_id-scoped queries. Supports 12-result limit, score normalization (FTS + vector combined).
- **Ingestion** (`app/services/knowledge_ingest.py`, `app/runtime/nodes/builtins/knowledge_ingest.py`): Async ingest of KnowledgeDocument objects into `kb_chunks` table. Supports custom chunk size/overlap. Stores user_id + doc_id + embedding (pgvector). Node interface exposes doc_id, text, source, filename, mime_type, title.
- **Source management** (`app/api/products/customer_service/knowledge.py`, `app/domains/customer_service/services/knowledge.py`): Product-layer API for add/edit/delete, workspace_id-scoped. Supports 4 source kinds: inline text, URL crawl (up to max_pages, HTML text extraction), file upload (PDF via pypdf, text/CSV/markdown via UTF-8), Shopify product/policy sync. Size limit 15 MB per file. Admin role required.
- **Knowledge application** (`ai_reply_composer.py`): Composer receives knowledge_context dict with retrieved hits, applies minimum score threshold from settings, tracks citation count, returns no-answer policy if no hits meet threshold.
- **Deletion** (`app/services/knowledge_documents.py`, knowledge.py:delete_source): Chunks deleted via `DELETE FROM kb_chunks WHERE user_id=? AND doc_id=?`. Workspace isolation enforced in delete_source via `_get_source()` which filters by workspace_id.
- **Settings & evaluation** (`knowledge.py`): Per-workspace settings (minimum_score, no_answer_policy, freshness_days, citations_required). Knowledge evaluation questions per workspace with pass/fail tracking against retrieval.
- **Models** (`models/models.py`): KBChunk, CustomerServiceKnowledgeSource, CustomerServiceKnowledgeSettings, CustomerServiceKnowledgeEvaluationQuestion. Sources have workspace_id PK; chunks have user_id + doc_id + content + embedding.
- **Tests**: Chunk stability/overlap (test_knowledge_service_contract.py), HTTP boundary architecture (test_knowledge_http_boundary.py), search mocking (test_customer_service_knowledge.py), ingestion tests for different file types.

**Is it good enough?**
Mostly yes for basic v1. Core retrieval and source management work. **Three gaps prevent "done":**
1. **user_id vs workspace_id mismatch** (CRITICAL): Product API uses workspace_id (correct tenant boundary), but core retrieval layer uses user_id. Mapping on line 64 (`get_settings(workspace_id=workspace_id, persist=False)` then `hybrid_search(..., user_id=user_id)`) suggests workspace_id is passed as user_id to search. This works only if workspace_id == user_id, which is not guaranteed. If a workspace has multiple users, only the workspace owner (user_id=workspace_id assumption?) retrieves knowledge correctly; others fail silently.
2. **No test verifying deleted knowledge vanishes from retrieval**: When delete_source() removes chunks, no test confirms the hits no longer appear in subsequent searches. Deletion could be broken and tests wouldn't catch it.
3. **AI doesn't distinguish retrieved knowledge from internal reasoning**: Reply composer receives knowledge_context but doesn't mark retrieved chunks separately from assumptions in its output. Per spec rule "AI distinguishes retrieved knowledge from assumptions," the AI should flag which statements come from merchant knowledge vs. learned behavior.

**Gaps / risks:**
- **Silent user_id/workspace_id bug**: Ambiguous parameter usage could cause cross-workspace knowledge leakage or retrieval failures on multi-user workspaces. Needs audit of actual workspace_id → user_id mapping at runtime.
- **Staleness of Shopify knowledge**: Shopify-synced sources are ingested but no test verifies freshness or re-sync behavior. If a product is deleted in Shopify, old knowledge may remain searchable.
- **No test for file upload failure cases**: Max 15 MB size limit has no test; PDF parse failures return 422 but behavior on corrupted PDFs untested.
- **Citation accuracy**: Citations reference doc_id (which is UUID for sources, or doc_* for inline), but user sees no clear mapping between citation and source name in response.

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Audit and fix user_id vs workspace_id boundary: trace the data flow in `app/domains/customer_service/services/knowledge.py:search_context` (line 62-71) to confirm workspace_id is correctly mapped to user_id at the core retrieval boundary. If workspace_id != user_id, update core search layer to accept workspace_id instead of user_id, or add an explicit conversion function. Add a test in `tests/customer_service/customers/test_customer_service_knowledge.py` that verifies search_context with workspace_id and a different user_id fails or returns workspace-scoped results only.
- [ ] Add test for deleted knowledge not in retrieval: in `tests/knowledge/`, create `test_knowledge_deletion.py` with a test that (1) ingests a document, (2) searches and confirms hit, (3) deletes the source via service, (4) searches again and confirms no hit from that doc_id, (5) verifies FTS and vector queries both exclude deleted chunks.
- [ ] Add knowledge attribution in AI replies: modify `app/domains/customer_service/services/ai_reply_composer.py` to add a `knowledge_sourced` flag or `source_type` field to each reply element, indicating which statements were retrieved from merchant knowledge (via citations) vs. internal AI knowledge. Update the reply schema to expose this distinction.
- [ ] Add test for file upload edge cases: in `tests/customer_service/customers/`, create `test_knowledge_file_ingest.py` with tests for (1) corrupted PDF (non-PDF binary disguised as .pdf), (2) 15 MB+ file rejection, (3) non-UTF-8 text file rejection, (4) successful multi-page PDF ingestion with per-page chunks.
- [ ] Add test for Shopify knowledge staleness and refresh: in `tests/customer_service/shopify/`, add a test that mocks shopify.sync(), ingests product knowledge, verifies retrieval, then re-syncs and confirms old product deletions are reflected (chunks removed).
- [ ] Verify workspace isolation in multi-user scenario: in `tests/customer_service/`, create `test_knowledge_workspace_isolation.py` with a test that (1) creates two workspaces, (2) ingests knowledge in workspace A with user A, (3) attempts search in workspace B with user B using workspace B's context, (4) confirms zero cross-workspace hits. 
