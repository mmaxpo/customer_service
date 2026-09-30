
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.tools.common.http import http
from app.api.mcp import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    await http.aclose()


app = FastAPI(lifespan=lifespan)

app.include_router(router, prefix="/mcp")