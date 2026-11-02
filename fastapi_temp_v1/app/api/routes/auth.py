from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth_service import EmailNotVerifiedError

from app.core.security import decode_access_token
from app.dependencies.auth import CurrentUser, DatabaseSession, bearer_scheme
from app.dependencies.database import get_db_session
from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    RefreshRequest,
    TokenResponse,
)
from app.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)

router = APIRouter()

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


def authentication_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authentication service temporarily unavailable.",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: DatabaseSession,
) -> TokenResponse:
    try:
        return await AuthService(session).login(
            email=str(payload.email).strip().casefold(),
            password=payload.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except RedisError as exc:
        raise authentication_unavailable() from exc

    except EmailNotVerifiedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    session: DatabaseSession,
) -> TokenResponse:
    try:
        return await AuthService(session).refresh(
            payload.refresh_token
        )
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        ) from exc
    except RedisError as exc:
        raise authentication_unavailable() from exc









@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: CurrentUser,
    access_credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme),
    ],
    session: DatabaseSession,
) -> LogoutResponse:
    try:
        await AuthService(session).logout(
            access_credentials.credentials,
            current_user,
        )
    except RedisError as exc:
        raise authentication_unavailable() from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return LogoutResponse(message="Logged out successfully.")




@router.post(
    "/logout-all",
    response_model=LogoutResponse,
)
async def logout_all(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> LogoutResponse:
    try:
        await AuthService(session).logout_all(current_user)
    except RedisError as exc:
        raise authentication_unavailable() from exc

    return LogoutResponse(
        message="All sessions have been logged out."
    )
