from __future__ import annotations

import asyncio
from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


@lru_cache(maxsize=1)
def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,
    )


async def embed_query(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Cannot embed empty query")

    emb = get_embeddings()
    vector = await asyncio.to_thread(emb.embed_query, text)

    _validate_vector(vector)

    return vector


async def embed_texts(texts: list[str]) -> list[list[float]]:
    clean_texts = [t for t in texts if t and t.strip()]

    if not clean_texts:
        return []

    emb = get_embeddings()
    vectors = await asyncio.to_thread(emb.embed_documents, clean_texts)

    for vector in vectors:
        _validate_vector(vector)

    return vectors


def _validate_vector(vector: list[float]) -> None:
    if len(vector) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Expected embedding dimension {EMBEDDING_DIMENSION}, got {len(vector)}"
        )
