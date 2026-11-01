
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