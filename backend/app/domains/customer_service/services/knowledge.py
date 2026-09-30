from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import logging
import socket
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import httpx
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.secrets import decrypt_secret
from app.core.config import settings as app_settings
from app.domains.customer_service.integrations.shopify.provider_factory import (
    ShopifyProviderFactory,
)
from app.domains.customer_service.models import (
    CustomerServiceKnowledgeEvaluationQuestion,
    CustomerServiceKnowledgeSettings,
    CustomerServiceKnowledgeSource,
)
from app.domains.customer_service.repositories.shopify import ShopifyRepository
from app.models.models import KBChunk
from app.services.knowledge_ingest import KnowledgeDocument, upsert_document_chunks
from app.services.knowledge_search import hybrid_search


logger = logging.getLogger(__name__)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text: list[str] = []
        self.links: list[str] = []
        self._ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self._ignored += 1
        if tag == "a" and not self._ignored:
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data):
        value = " ".join(data.split())
        if value and not self._ignored:
            self.text.append(value)


class CustomerServiceKnowledgeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_context(self, *, user_id, query: str, k: int = 5) -> dict:
        query = (query or "").strip()
        settings = await self.get_settings(workspace_id=user_id, persist=False)
        hits: list[dict] = []
        if query and app_settings.OPENAI_API_KEY:
            try:
                hits = await hybrid_search(
                    db=self.db, user_id=user_id, query=query, final_k=k, reranker=None
                )
            except Exception:
                # Knowledge retrieval is an enhancement to AI replies, not a
                # reason to break the Inbox composer. This also covers a
                # temporarily unavailable embedding provider (for example an
                # unset/expired OpenAI key); the composer can still produce a
                # safe low-confidence draft from conversation and Shopify
                # context, while the provider failure remains observable.
                logger.warning(
                    "customer_service_knowledge_search_unavailable",
                    exc_info=True,
                    extra={"workspace_id": str(user_id)},
                )
        elif query and not app_settings.OPENAI_API_KEY:
            logger.warning(
                "customer_service_knowledge_search_skipped_missing_embedding_key",
                extra={"workspace_id": str(user_id)},
            )
        normalized = [self._normalize_hit(hit) for hit in hits]
        best = max((item["score"] or 0.0 for item in normalized), default=0.0)
        answered = bool(normalized) and best >= settings.minimum_score
        citations = (
            [
                {
                    "source_id": item["doc_id"],
                    "title": item["title"] or item["filename"],
                    "url": item["source"],
                    "page": item["page"],
                    "chunk_index": item["chunk_index"],
                }
                for item in normalized
            ]
            if answered
            else []
        )
        return {
            "query": query,
            "context": self._build_context(normalized) if answered else "",
            "hits": normalized if answered else [],
            "answered": answered,
            "no_answer_policy": None if answered else settings.no_answer_policy,
            "no_answer_message": None if answered else settings.no_answer_message,
            "citations": citations,
        }

    async def list_sources(self, *, workspace_id):
        settings = await self.get_settings(workspace_id=workspace_id, persist=False)
        rows = await self.db.scalars(
            select(CustomerServiceKnowledgeSource)
            .where(CustomerServiceKnowledgeSource.workspace_id == workspace_id)
            .order_by(CustomerServiceKnowledgeSource.created_at.desc())
        )
        sources = list(rows.all())
        stale_before = datetime.now(timezone.utc) - timedelta(
            days=settings.freshness_days
        )
        for source in sources:
            if (
                source.last_indexed_at is not None
                and source.last_indexed_at < stale_before
                and source.status == "ready"
            ):
                source.freshness_status = "stale"
        return sources

    async def ingest_inline(self, *, workspace_id, actor_user_id, name, text):
        return await self._create_and_index(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            kind="inline",
            name=name,
            source_uri=None,
            external_id=str(uuid4()),
            content=text,
            documents=[KnowledgeDocument(text=text, source="inline", title=name)],
        )

    async def ingest_url(self, *, workspace_id, actor_user_id, url, name, max_pages):
        pages = await self._crawl(url=url, max_pages=max_pages)
        if not pages:
            raise HTTPException(
                status_code=422, detail="URL did not contain indexable text"
            )
        documents = [
            KnowledgeDocument(
                text=page["text"], source=page["url"], title=page["title"]
            )
            for page in pages
        ]
        content = "\n\n".join(f"# {page['title']}\n{page['text']}" for page in pages)
        return await self._create_and_index(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            kind="url",
            name=name or pages[0]["title"],
            source_uri=url,
            external_id=url,
            content=content,
            documents=documents,
            meta={"pages_crawled": len(pages)},
        )

    async def ingest_file(
        self, *, workspace_id, actor_user_id, filename, content_type, data
    ):
        if len(data) > 15 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Knowledge file exceeds 15 MB")
        if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
            try:
                from pypdf import PdfReader

                reader = PdfReader(BytesIO(data))
                documents = [
                    KnowledgeDocument(
                        text=page.extract_text() or "",
                        source=filename,
                        filename=filename,
                        mime_type="application/pdf",
                        page=index + 1,
                        title=filename,
                    )
                    for index, page in enumerate(reader.pages)
                ]
            except Exception as exc:
                raise HTTPException(
                    status_code=422, detail="Could not read PDF"
                ) from exc
        elif content_type.startswith("text/") or filename.lower().endswith(
            (".txt", ".md", ".csv")
        ):
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise HTTPException(
                    status_code=422, detail="Text file must be UTF-8"
                ) from exc
            documents = [
                KnowledgeDocument(
                    text=text,
                    source=filename,
                    filename=filename,
                    mime_type=content_type,
                    title=filename,
                )
            ]
        else:
            raise HTTPException(
                status_code=415, detail="Only PDF and text files are supported"
            )
        documents = [doc for doc in documents if doc.text.strip()]
        if not documents:
            raise HTTPException(
                status_code=422, detail="File contained no indexable text"
            )
        content = "\n\n".join(doc.text for doc in documents)
        return await self._create_and_index(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            kind="file",
            name=filename,
            source_uri=filename,
            external_id=str(uuid4()),
            content=content,
            documents=documents,
            meta={"content_type": content_type, "bytes": len(data)},
        )

    async def sync_shopify(self, *, workspace_id, actor_user_id):
        connection = await ShopifyRepository(self.db).get_active_connection(
            user_id=workspace_id
        )
        if connection is None:
            raise HTTPException(
                status_code=404, detail="No active Shopify connection found"
            )
        provider = ShopifyProviderFactory.create()
        loader = getattr(provider, "list_knowledge_content", None)
        if loader is None:
            raise HTTPException(
                status_code=503, detail="Shopify content sync is unavailable"
            )
        items = await loader(
            shop_domain=connection.shop_domain,
            access_token=decrypt_secret(connection.access_token_encrypted),
        )
        synced = []
        for item in items:
            source = await self.db.scalar(
                select(CustomerServiceKnowledgeSource).where(
                    CustomerServiceKnowledgeSource.workspace_id == workspace_id,
                    CustomerServiceKnowledgeSource.kind == item["kind"],
                    CustomerServiceKnowledgeSource.external_id == item["external_id"],
                )
            )
            documents = [
                KnowledgeDocument(
                    text=item["content"], source=item.get("url"), title=item["title"]
                )
            ]
            if source:
                source.name = item["title"]
                source.source_uri = item.get("url")
                source.content = item["content"]
                source.meta = item.get("meta") or {}
                synced.append(await self._index_source(source, documents=documents))
            else:
                synced.append(
                    await self._create_and_index(
                        workspace_id=workspace_id,
                        actor_user_id=actor_user_id,
                        kind=item["kind"],
                        name=item["title"],
                        source_uri=item.get("url"),
                        external_id=item["external_id"],
                        content=item["content"],
                        documents=documents,
                        meta=item.get("meta") or {},
                    )
                )
        return synced

    async def reindex(self, *, workspace_id, source_id):
        source = await self._get_source(workspace_id=workspace_id, source_id=source_id)
        return await self._index_source(source)

    async def delete_source(self, *, workspace_id, source_id):
        source = await self._get_source(workspace_id=workspace_id, source_id=source_id)
        await self.db.execute(
            delete(KBChunk).where(
                KBChunk.user_id == workspace_id, KBChunk.doc_id == str(source.id)
            )
        )
        await self.db.delete(source)
        await self.db.commit()

    async def get_settings(self, *, workspace_id, persist: bool = True):
        settings = await self.db.get(CustomerServiceKnowledgeSettings, workspace_id)
        if settings is None:
            settings = CustomerServiceKnowledgeSettings(
                workspace_id=workspace_id,
                no_answer_policy="handoff",
                no_answer_message=(
                    "I don't have enough verified information. "
                    "I'll hand this to a person."
                ),
                minimum_score=0.0,
                freshness_days=30,
                citations_required=True,
            )
            if persist:
                self.db.add(settings)
                await self.db.commit()
                await self.db.refresh(settings)
        return settings

    async def update_settings(self, *, workspace_id, payload):
        settings = await self.get_settings(workspace_id=workspace_id)
        for field, value in payload.model_dump().items():
            setattr(settings, field, value)
        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    async def create_evaluation(self, *, workspace_id, payload):
        question = CustomerServiceKnowledgeEvaluationQuestion(
            workspace_id=workspace_id, **payload.model_dump()
        )
        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        return question

    async def list_evaluations(self, *, workspace_id):
        rows = await self.db.scalars(
            select(CustomerServiceKnowledgeEvaluationQuestion).where(
                CustomerServiceKnowledgeEvaluationQuestion.workspace_id == workspace_id
            )
        )
        return list(rows.all())

    async def run_evaluations(self, *, workspace_id):
        questions = await self.list_evaluations(workspace_id=workspace_id)
        results = []
        for question in questions:
            if not question.is_active:
                continue
            retrieval = await self.search_context(
                user_id=workspace_id, query=question.question
            )
            results.append(
                {
                    "question_id": str(question.id),
                    "question": question.question,
                    "passed": retrieval["answered"],
                    "citation_count": len(retrieval["citations"]),
                    "expected_answer": question.expected_answer,
                }
            )
        return {
            "total": len(results),
            "passed": sum(r["passed"] for r in results),
            "results": results,
        }

    async def _create_and_index(
        self,
        *,
        workspace_id,
        actor_user_id,
        kind,
        name,
        source_uri,
        external_id,
        content,
        documents,
        meta=None,
    ):
        existing = await self.db.scalar(
            select(CustomerServiceKnowledgeSource).where(
                CustomerServiceKnowledgeSource.workspace_id == workspace_id,
                CustomerServiceKnowledgeSource.kind == kind,
                CustomerServiceKnowledgeSource.external_id == external_id,
            )
        )
        if existing is not None:
            existing.name = name
            existing.source_uri = source_uri
            existing.content = content
            existing.meta = meta or {}
            return await self._index_source(existing, documents=documents)
        source = CustomerServiceKnowledgeSource(
            workspace_id=workspace_id,
            kind=kind,
            name=name,
            source_uri=source_uri,
            external_id=external_id,
            content=content,
            status="indexing",
            freshness_status="indexing",
            meta=meta or {},
            created_by_user_id=actor_user_id,
        )
        self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)
        return await self._index_source(source, documents=documents)

    async def _index_source(self, source, documents=None):
        now = datetime.now(timezone.utc)
        source.status = source.freshness_status = "indexing"
        source.last_checked_at = now
        documents = documents or [
            KnowledgeDocument(
                text=source.content or "",
                source=source.source_uri,
                filename=source.name if source.kind == "file" else None,
                title=source.name,
            )
        ]
        try:
            chunks = await upsert_document_chunks(
                self.db,
                user_id=source.workspace_id,
                doc_id=str(source.id),
                documents=documents,
            )
            if not chunks:
                raise ValueError("No indexable content")
            source.content_hash = hashlib.sha256(
                (source.content or "").encode()
            ).hexdigest()
            source.status = "ready"
            source.freshness_status = "fresh"
            source.last_indexed_at = now
            source.error = None
            source.meta = {**(source.meta or {}), "chunks": chunks}
            await self.db.commit()
            await self.db.refresh(source)
            return source
        except Exception as exc:
            await self.db.rollback()
            persisted = await self.db.get(CustomerServiceKnowledgeSource, source.id)
            if persisted:
                persisted.status = persisted.freshness_status = "failed"
                persisted.error = str(exc)[:2000]
                await self.db.commit()
            raise

    async def _get_source(self, *, workspace_id, source_id):
        source = await self.db.scalar(
            select(CustomerServiceKnowledgeSource).where(
                CustomerServiceKnowledgeSource.id == source_id,
                CustomerServiceKnowledgeSource.workspace_id == workspace_id,
            )
        )
        if source is None:
            raise HTTPException(status_code=404, detail="Knowledge source not found")
        return source

    async def _crawl(self, *, url, max_pages):
        root = self._normalize_url(url)
        root_host = urlparse(root).hostname
        queue, seen, pages = [root], set(), []
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            while queue and len(pages) < max_pages:
                current = queue.pop(0)
                if current in seen:
                    continue
                seen.add(current)
                await self._assert_public_url(current)
                response = await client.get(
                    current, headers={"User-Agent": "TajeranKnowledgeBot/1.0"}
                )
                if response.is_redirect:
                    continue
                response.raise_for_status()
                if len(
                    response.content
                ) > 2 * 1024 * 1024 or "text/html" not in response.headers.get(
                    "content-type", ""
                ):
                    continue
                parser = _HTMLTextExtractor()
                parser.feed(response.text)
                text = "\n".join(parser.text).strip()
                if text:
                    title = next(
                        (part for part in parser.text[:10] if len(part) <= 255), current
                    )
                    pages.append({"url": current, "title": title, "text": text})
                for link in parser.links:
                    candidate = urljoin(current, link).split("#", 1)[0]
                    parsed = urlparse(candidate)
                    if (
                        parsed.scheme in {"http", "https"}
                        and parsed.hostname == root_host
                    ):
                        queue.append(candidate)
        return pages

    @staticmethod
    def _normalize_url(url):
        parsed = urlparse((url or "").strip())
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
        ):
            raise HTTPException(
                status_code=422, detail="A public HTTP(S) URL is required"
            )
        return parsed.geturl()

    @staticmethod
    async def _assert_public_url(url):
        host = urlparse(url).hostname
        try:
            addresses = await asyncio.to_thread(socket.getaddrinfo, host, None)
        except socket.gaierror as exc:
            raise HTTPException(
                status_code=422, detail="Knowledge URL cannot be resolved"
            ) from exc
        if any(
            not ipaddress.ip_address(address[4][0]).is_global for address in addresses
        ):
            raise HTTPException(
                status_code=422, detail="Private knowledge URLs are not allowed"
            )

    @staticmethod
    def _normalize_hit(hit):
        score = (
            hit.get("score_rerank")
            or hit.get("score_hybrid")
            or hit.get("score_vec")
            or hit.get("score_fts")
        )
        return {
            "doc_id": hit.get("doc_id"),
            "title": hit.get("title"),
            "filename": hit.get("filename"),
            "content": hit.get("content") or "",
            "score": float(score) if score is not None else None,
            "source": hit.get("source"),
            "page": hit.get("page"),
            "chunk_index": hit.get("chunk_index"),
        }

    @staticmethod
    def _build_context(hits):
        return "\n\n".join(
            f"[{index}] {hit.get('title') or hit.get('filename') or hit.get('doc_id') or 'Knowledge'}\n{hit['content'].strip()}"
            for index, hit in enumerate(hits, start=1)
            if hit.get("content", "").strip()
        )
