from fastapi import Header, HTTPException

from app.core.config import settings


async def require_api_key(x_api_key: str = Header(...)):

    if x_api_key != settings.MCP_API_KEY:
        raise HTTPException(401, "Invalid API Key")
