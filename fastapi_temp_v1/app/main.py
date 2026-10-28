from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import get_settings
from app.db.session import engine

@asynccontextmanager
async def lifespan(app:FastAPI):
    yield
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title= settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)


@app.get("/api/v1/health/live", tags=["Health"])
async def liveness_check()-> dict[str,str]:
    return {"status": "alive"}


@app.get("/", tags=["Health"])
async def root()-> dict[str,str]:
    return {
        "message": "ShvetVarni FastAPI Template",
        "status": "running",
    }