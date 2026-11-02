
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.dependencies.auth import CurrentUser
from app.dependencies.database import get_db_session
from app.schemas.user import UserCreate, UserRead, UserProfileUpdate
from app.services.user_service import (
    UserAlreadyExistsError,
    UserService,
)


import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from app.db.models.email_verification_token import EmailVerificationToken

router = APIRouter()


DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user",
)
async def register_user(
    payload: UserCreate,
    session: DatabaseSession,
) -> UserRead:
    service = UserService(session)

    try:
        user = await service.register_user(payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return UserRead.model_validate(user)



@router.post(
    "/verify-email",
    status_code=status.HTTP_200_OK,
    summary="Verify an email address",
)
async def verify_email(
    token: str,
    session: DatabaseSession,
) -> dict[str, str]:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)

    async with session.begin():
        result = await session.execute(
            select(EmailVerificationToken)
            .where(EmailVerificationToken.token_hash == token_hash)
            .with_for_update()
        )
        verification_token = result.scalar_one_or_none()

        if verification_token is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification link.",
            )

        if verification_token.consumed_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification link.",
            )

        # Normalize to UTC if a database driver returns a naive timestamp.
        expiry = verification_token.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if expiry <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification link.",
            )

        user_result = await session.execute(
            select(User).where(User.id == verification_token.user_id)
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification link.",
            )

        user.is_verified = True
        verification_token.consumed_at = now

    return {"message": "Email verified successfully."}


@router.get("/me", response_model=UserRead)
async def get_my_profile(
    current_user: CurrentUser,
) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_my_profile(
    payload: UserProfileUpdate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> User:
    service = UserService(session)
    return await service.update_profile(
        current_user,
        payload,
    )