
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_db_session
from app.schemas.user import UserCreate, UserRead
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
