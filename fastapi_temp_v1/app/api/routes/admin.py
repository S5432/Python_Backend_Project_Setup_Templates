from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.constants import ROLE_ADMIN, ROLE_USER
from app.db.models.user import User
from app.dependencies.auth import CurrentUser
from app.dependencies.permissions import RequireAdmin, require_role

router = APIRouter()


@router.get("/me", summary="Admin-only test endpoint")
async def admin_only(current_user: RequireAdmin) -> dict[str, str]:
    return {"message": "Admin access granted", "user_id": str(current_user.id)}


@router.get("/user-area", summary="Endpoint available to any authenticated user")
async def user_area(
    current_user: User = Depends(require_role(ROLE_USER, ROLE_ADMIN)),
) -> dict[str, str]:
    return {"message": "Authenticated access granted", "user_id": str(current_user.id)}


@router.get("/resources/{owner_id}", summary="Object-level authorization test")
async def read_user_resource(owner_id: UUID, current_user: CurrentUser) -> dict[str, str]:
    """A user may read their own resource; admins may read any user's resource."""
    if current_user.id != owner_id and ROLE_ADMIN not in {
        role.name for role in current_user.roles
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only access your own resource.",
        )
    return {
        "resource_owner_id": str(owner_id),
        "accessed_by": str(current_user.id),
    }
