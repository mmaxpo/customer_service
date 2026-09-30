from fastapi import APIRouter, Depends
from pydantic import BaseModel,Field

from app.core.auth import require_api_key
from app.tools.search.router import router as search_router
from app.tools.web_extract.router import router as web_extract_router

router = APIRouter()


class SearchReq(BaseModel):
    query: str
    k: int = 5


@router.post("/search", dependencies=[Depends(require_api_key)])
async def search(req: SearchReq):

    return {"results": await search_router.search(req.query, req.k)}

class ExtractReq(BaseModel):
    url: str
    mode: str = "article"
    include_html: bool = False
    max_chars: int = Field(default=200_000, ge=1, le=2_000_000)

@router.post("/extract", dependencies=[Depends(require_api_key)])
async def extract(req: ExtractReq):
    r = await web_extract_router.extract(
        url=req.url,
        mode=req.mode,
        include_html=req.include_html,
        max_chars=req.max_chars,
    )
    return {
        "ok": r.ok,
        "url": r.url,
        "title": r.title,
        "text": r.text,
        "html": r.html,
        "meta": r.meta or {},
    }