from fastapi import APIRouter

from app.api.routes import health, users, auth, admin

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


api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    admin.router, 
    prefix="/rbac", 
    tags=["RBAC and Authorization"],
)
