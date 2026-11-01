from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.redis_client import redis_client
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast if Redis is unavailable. Authentication
    # should not start in a partially functional state.
    await redis_client.ping()

    try:
        yield
    finally:
        await redis_client.aclose()
        await engine.dispose()