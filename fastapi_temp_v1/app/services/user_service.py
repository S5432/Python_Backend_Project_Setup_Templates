
import asyncio

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate


class UserAlreadyExistsError(Exception):
    """Raised when an email address is already registered."""


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = UserRepository(session)

    async def register_user(
        self,
        payload: UserCreate,
    ) -> User:
        email = str(payload.email).strip().casefold()

        try:
            async with self.session.begin():
                existing_user = (
                    await self.repository.get_by_email(email)
                )

                if existing_user is not None:
                    raise UserAlreadyExistsError(
                        "An account with this email already exists."
                    )

                hashed_password = await asyncio.to_thread(
                    hash_password,
                    payload.password,
                )

                user = await self.repository.create(
                    email=email,
                    full_name=payload.full_name,
                    hashed_password=hashed_password,
                )

            return user

        except IntegrityError as exc:
            # PostgreSQL's unique index remains the final
            # protection against concurrent registrations.
            raise UserAlreadyExistsError(
                "An account with this email already exists."
            ) from exc
