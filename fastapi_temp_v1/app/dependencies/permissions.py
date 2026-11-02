from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.core.constants import ROLE_ADMIN
from app.db.models.user import User
from app.dependencies.auth import CurrentUser


def require_role(*allowed_roles: str) -> Callable:
    """Build a dependency that requires at least one database-backed role."""
    required = frozenset(allowed_roles)

    async def role_checker(current_user: CurrentUser) -> User:
        actual = {role.name for role in current_user.roles}
        if not actual.intersection(required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return role_checker


RequireAdmin = Annotated[User, Depends(require_role(ROLE_ADMIN))]
