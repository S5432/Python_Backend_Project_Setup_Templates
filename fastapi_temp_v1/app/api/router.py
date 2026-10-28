from fastapi import APIRouter

from app.api.routes import health, users

api_router = APIRouter()

api_router.include_router(
    health.router,
    prefix="/health"
)


api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)