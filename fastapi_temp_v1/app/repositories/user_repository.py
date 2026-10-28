
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(
        self,
        email: str,
    ) -> User | None:
        statement = select(User).where(
            func.lower(User.email) == email.casefold()
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        return await self.session.get(User, user_id)

    async def create(
        self,
        *,
        email: str,
        full_name: str | None,
        hashed_password: str,
    ) -> User:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
        )

        self.session.add(user)

        # Send the INSERT to PostgreSQL without committing
        # the surrounding service transaction.
        await self.session.flush()
        await self.session.refresh(user)

        return user
