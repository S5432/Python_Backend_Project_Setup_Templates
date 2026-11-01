
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import redis_client
from app.core.security import decode_access_token
from app.db.models.user import User
from app.dependencies.database import get_db_session
from app.repositories.user_repository import UserRepository


bearer_scheme = HTTPBearer(auto_error=False)

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: DatabaseSession,
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    token = credentials.credentials

    try:
        claims = decode_access_token(token)
        user_id = UUID(claims["sub"])
        token_version = int(claims["ver"])
        jti = claims["jti"]
        family_id = claims.get("sid")
    except (InvalidTokenError, ValueError, KeyError, TypeError):
        raise unauthorized

    try:
        revoked = await redis_client.get(f"auth:revoked:{jti}")

        family_revoked = None
        if family_id is not None:
            family_revoked = await redis_client.get(
                f"auth:revoked-family:{family_id}"
            )
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable.",
        ) from exc

    if revoked is not None or family_revoked is not None:
        raise unauthorized

    user = await UserRepository(session).get_by_id(user_id)

    if user is None or not user.is_active:
        raise unauthorized

    if user.token_version != token_version:
        raise unauthorized

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
