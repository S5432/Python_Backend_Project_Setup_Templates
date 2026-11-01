from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_hash_for_update(
        self,
        token_hash: str,
    ) -> RefreshToken | None:
        statement = (
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        family_id: UUID,
        expires_at: datetime,
    ) -> RefreshToken:
        record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def revoke_family(self, family_id: UUID) -> None:
        statement = (
            select(RefreshToken)
            .where(RefreshToken.family_id == family_id)
            .with_for_update()
        )
        result = await self.session.execute(statement)

        for record in result.scalars():
            record.revoked_at = datetime.now(timezone.utc)
            record.is_revoked = True

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        statement = (
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .with_for_update()
        )
        result = await self.session.execute(statement)

        now = datetime.now(timezone.utc)
        for record in result.scalars():
            record.revoked_at = now
            record.is_revoked = True