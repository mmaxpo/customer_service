from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_ingest import (
    KnowledgeDocument,
    upsert_document_chunks,
)
from app.tools.common.logging import tool_span
from app.tools.common.types import ToolResult


class KnowledgeIngestService:
    async def ingest_text(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        text: str,
        *,
        doc_id: str | None = None,
        source: str | None = None,
        filename: str | None = None,
        mime_type: str | None = "text/plain",
        title: str | None = None,
    ) -> ToolResult:
        doc_id = doc_id or str(uuid.uuid4())

        document = KnowledgeDocument(
            text=text,
            source=source,
            filename=filename,
            mime_type=mime_type,
            title=title,
        )

        with tool_span(
            "knowledge_ingest",
            doc_id=doc_id,
            source=source,
            filename=filename,
        ):
            chunks = await upsert_document_chunks(
                db=db,
                user_id=user_id,
                doc_id=doc_id,
                documents=[document],
            )

        return ToolResult(
            content=f"Ingested {chunks} chunks into knowledge base.",
            artifact={
                "doc_id": doc_id,
                "chunks": chunks,
                "source": source,
                "filename": filename,
                "title": title,
            },
        )
