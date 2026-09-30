import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage

from app.core.session import get_db as get_session
from app.tenancy.context import get_current_principal as get_current_user
from app.services.knowledge_documents import (
    delete_knowledge_document,
    list_knowledge_documents,
)
from app.services.knowledge_ingest import upsert_document_chunks
from app.services.knowledge_search import hybrid_search

router = APIRouter(prefix="/kb", tags=["knowledge"])


class SearchReq(BaseModel):
    query: str
    top_k: int = 8


@router.post("/search")
async def kb_search(
    req: SearchReq,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
    request: Request = None,
):
    reranker = getattr(request.app.state, "reranker", None)
    results = await hybrid_search(
        db=db,
        user_id=current_user.workspace_id,
        query=req.query,
        final_k=req.top_k,
        reranker=reranker,
    )
    return {"query": req.query, "results": results}


@router.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest(
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    user_id = current_user.workspace_id
    ct = (request.headers.get("content-type") or "").lower()

    docs: List[Document] = []
    doc_id = None

    if ct.startswith("application/json"):
        data = await request.json()
        texts = data.get("texts")
        doc_id = data.get("doc_id") or str(
            uuid.uuid4()
        )  # allow client to pass stable doc_id
        if not isinstance(texts, list):
            raise HTTPException(422, detail="'texts' must be an array.")
        for t in texts:
            s = (t or "").strip()
            if not s:
                continue
            docs.append(
                Document(
                    page_content=s,
                    metadata={
                        "source": "inline",
                        "filename": None,
                        "mime_type": "text/plain",
                        "page": None,
                        "title": None,
                    },
                )
            )

    else:
        raise HTTPException(
            415,
            detail="For now, send JSON {texts:[...], doc_id?:...}. Add file support next.",
        )

    if not docs:
        raise HTTPException(400, detail="No content to ingest.")

    inserted = await upsert_document_chunks(
        db, user_id=user_id, doc_id=doc_id, docs=docs
    )
    return {"user_id": str(user_id), "doc_id": doc_id, "chunks": inserted}


@router.delete("/docs/{doc_id}")
async def delete_doc(
    doc_id: str,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    await delete_knowledge_document(
        db,
        user_id=current_user.workspace_id,
        doc_id=doc_id,
    )
    return {"ok": True, "doc_id": doc_id}


@router.get("/docs")
async def list_docs(
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    docs = await list_knowledge_documents(
        db,
        user_id=current_user.workspace_id,
    )

    return {"docs": docs}


class AskReq(BaseModel):
    message: str
    thread_id: Optional[str] = None


@router.post("/ask_agent")
async def ask_agent(
    req: AskReq,
    request: Request,
    current_user=Depends(get_current_user),
    debug: bool = Query(False),
):
    agent = request.app.state.knowledge_agent

    thread_id = req.thread_id or str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": str(current_user.workspace_id),
        }
    }

    out = await agent.ainvoke(
        {
            "messages": [HumanMessage(content=req.message)],
            "user_id": str(current_user.workspace_id),
        },
        config=config,
    )

    reply = out["messages"][-1].content

    # --- citations / sources
    retrieved = out.get("retrieved") or []
    sources = [
        {
            "id": r.get("id"),
            "doc_id": r.get("doc_id"),
            "chunk_index": r.get("chunk_index"),
            "page": r.get("page"),
            "filename": r.get("filename"),
            "scores": {
                "fts": r.get("score_fts"),
                "vec": r.get("score_vec"),
                "hybrid": r.get("score_hybrid"),
                "rerank": r.get("score_rerank"),
            },
        }
        for r in retrieved
    ]

    payload = {"reply": reply, "thread_id": thread_id, "sources": sources}

    # --- optional debug
    if debug:
        payload["debug"] = {
            "retrieved_count": len(retrieved),
            "context_preview": out.get("context"),
        }

    return payload


@router.post("/ask_agent_mcp")
async def ask_agent_mcp(
    req: AskReq,
    request: Request,
    current_user=Depends(get_current_user),
    debug: bool = Query(False),
):
    agent = request.app.state.knowledge_agent

    thread_id = req.thread_id or str(uuid.uuid4())

    # ✅ IMPORTANT: include user_id in config
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": str(current_user.workspace_id),
        }
    }

    out = await agent.ainvoke(
        {
            "messages": [HumanMessage(content=req.message)],
        },
        config=config,
    )

    reply = out["messages"][-1].content
    return {"reply": reply, "thread_id": thread_id}
