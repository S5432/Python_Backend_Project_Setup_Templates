from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.role import Role
from app.db.models.user import User


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_name(self, name: str) -> Role | None:
        result = await self.session.execute(
            select(Role).where(Role.name == name)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, name: str, description: str | None = None) -> Role:
        role = await self.get_by_name(name)
        if role is None:
            role = Role(name=name, description=description)
            self.session.add(role)
            await self.session.flush()
        return role

    async def assign(self, user: User, role_name: str) -> None:
        role = await self.get_by_name(role_name)
        if role is None:
            raise ValueError(f"Role {role_name!r} is not provisioned.")
        if all(existing.name != role_name for existing in user.roles):
            user.roles.append(role)
            await self.session.flush()
