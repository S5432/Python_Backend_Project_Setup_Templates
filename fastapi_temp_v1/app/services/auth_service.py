
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis_client import redis_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_refresh_token,
    verify_password_async,
)
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User
from app.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse


class InvalidCredentialsError(Exception):
    """Login credentials are invalid."""


class InvalidRefreshTokenError(Exception):
    """Refresh token is invalid, expired, revoked, or reused."""


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.settings = get_settings()

    def _issue_access_token(
        self,
        user: User,
        family_id: UUID,
    ) -> tuple[str, int]:
        token, _, expires_at = create_access_token(
            user_id=user.id,
            token_version=user.token_version,
            family_id=family_id,
        )
        seconds = max(
            1,
            int((expires_at - datetime.now(timezone.utc)).total_seconds()),
        )
        return token, seconds

    async def login(
        self,
        *,
        email: str,
        password: str,
    ) -> TokenResponse:
        async with self.session.begin():
            user = await self.users.get_by_email(
                email.strip().casefold()
            )

            if user is None:
                raise InvalidCredentialsError()

            valid_password = await verify_password_async(
                password,
                user.hashed_password,
            )

            if not valid_password or not user.is_active:
                raise InvalidCredentialsError()

            family_id = uuid4()
            raw_refresh_token = create_refresh_token()
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=self.settings.refresh_token_days
            )

            await self.refresh_tokens.create(
                user_id=user.id,
                token_hash=hash_refresh_token(raw_refresh_token),
                family_id=family_id,
                expires_at=expires_at,
            )

            access_token, expires_in = self._issue_access_token(
                user,
                family_id,
            )

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            expires_in=expires_in,
        )

    async def refresh(
        self,
        raw_token: str,
    ) -> TokenResponse:
        now = datetime.now(timezone.utc)
        invalid = False
        result: TokenResponse | None = None
        family_to_revoke: UUID | None = None

        # Do not raise inside this transaction when replay is detected:
        # we must commit the family revocation before returning 401.
        async with self.session.begin():
            record = await self.refresh_tokens.get_by_hash_for_update(
                hash_refresh_token(raw_token)
            )

            if record is None:
                invalid = True

            elif (
                record.is_revoked
                or record.revoked_at is not None
                or record.replaced_by_id is not None
            ):
                family_to_revoke = record.family_id
                await self.refresh_tokens.revoke_family(
                    record.family_id
                )
                invalid = True

            elif record.expires_at <= now:
                family_to_revoke = record.family_id
                await self.refresh_tokens.revoke_family(
                    record.family_id
                )
                invalid = True

            else:
                user_result = await self.session.execute(
                    select(User)
                    .where(User.id == record.user_id)
                    .with_for_update()
                )
                user = user_result.scalar_one_or_none()

                if user is None or not user.is_active:
                    family_to_revoke = record.family_id
                    await self.refresh_tokens.revoke_family(
                        record.family_id
                    )
                    invalid = True

                else:
                    new_raw_token = create_refresh_token()
                    new_expires_at = now + timedelta(
                        days=self.settings.refresh_token_days
                    )

                    replacement = await self.refresh_tokens.create(
                        user_id=user.id,
                        token_hash=hash_refresh_token(new_raw_token),
                        family_id=record.family_id,
                        expires_at=new_expires_at,
                    )

                    record.revoked_at = now
                    record.is_revoked = True
                    record.replaced_by_id = replacement.id

                    access_token, expires_in = (
                        self._issue_access_token(
                            user,
                            record.family_id,
                        )
                    )

                    result = TokenResponse(
                        access_token=access_token,
                        refresh_token=new_raw_token,
                        expires_in=expires_in,
                    )

        if family_to_revoke is not None:
            # If Redis is unavailable, protected APIs fail closed.
            # The database revocation has already been committed.
            await redis_client.set(
                f"auth:revoked-family:{family_to_revoke}",
                "1",
                ex=max(
                    1,
                    self.settings.refresh_token_days * 86400,
                ),
            )

        if invalid or result is None:
            raise InvalidRefreshTokenError()

        return result

    async def logout(
        self,
        access_token: str,
        user: User,
    ) -> None:
        try:
            claims = decode_access_token(access_token)
            jti = claims["jti"]
            exp = int(claims["exp"])
            sid = claims.get("sid")
        except (InvalidTokenError, KeyError, TypeError, ValueError):
            raise InvalidCredentialsError()

        now_ts = int(datetime.now(timezone.utc).timestamp())
        remaining = exp - now_ts

        if remaining > 0:
            await redis_client.set(
                f"auth:revoked:{jti}",
                "1",
                ex=remaining,
            )

        if sid:
            family_id = UUID(sid)
            await redis_client.set(
                f"auth:revoked-family:{family_id}",
                "1",
                ex=max(
                    1,
                    self.settings.refresh_token_days * 86400,
                ),
            )

            await self.refresh_tokens.revoke_family(family_id)

        await self.session.commit()

    async def logout_all(self, user: User) -> None:
        # The authenticated-user dependency has already queried this
        # session. Reuse its transaction rather than nesting begin().
        user.token_version += 1
        await self.refresh_tokens.revoke_all_for_user(user.id)
        await self.session.commit()
