
import asyncio
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.db.models.email_verification_token import EmailVerificationToken
from app.workers.tasks.email_tasks import send_verification_email_task

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate
from app.schemas.user import UserProfileUpdate


logger = logging.getLogger(__name__)
settings = get_settings()


class UserAlreadyExistsError(Exception):
    """Raised when an email address is already registered."""


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = UserRepository(session)

    # async def register_user(
    #     self,
    #     payload: UserCreate,
    # ) -> User:
    #     email = str(payload.email).strip().casefold()

    #     try:
    #         async with self.session.begin():
    #             existing_user = (
    #                 await self.repository.get_by_email(email)
    #             )

    #             if existing_user is not None:
    #                 raise UserAlreadyExistsError(
    #                     "An account with this email already exists."
    #                 )

    #             hashed_password = await asyncio.to_thread(
    #                 hash_password,
    #                 payload.password,
    #             )

    #             user = await self.repository.create(
    #                 email=email,
    #                 full_name=payload.full_name,
    #                 hashed_password=hashed_password,
    #             )

    #         return user

    #     except IntegrityError as exc:
    #         # PostgreSQL's unique index remains the final
    #         # protection against concurrent registrations.
    #         raise UserAlreadyExistsError(
    #             "An account with this email already exists."
    #         ) from exc

    
    async def register_user(self, payload: UserCreate) -> User:
        email = str(payload.email).strip().casefold()
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        try:
            async with self.session.begin():
                existing_user = await self.repository.get_by_email(email)

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

                # New accounts are unverified until the link is consumed.
                user.is_verified = False

                verification_token = EmailVerificationToken(
                    user_id=user.id,
                    token_hash=token_hash,
                    expires_at=(
                        datetime.now(timezone.utc)
                        + timedelta(
                            minutes=settings.email_verification_token_minutes
                        )
                    ),
                )

                self.session.add(verification_token)
                await self.session.flush()

        except IntegrityError as exc:
            raise UserAlreadyExistsError(
                "An account with this email already exists."
            ) from exc

        # The database transaction has committed before publishing the task.
        try:
            send_verification_email_task.delay(
                email,
                user.full_name,
                raw_token,
            )
        except Exception:
            # Do not log the raw token, email body, or verification URL.
            logger.exception(
                "Could not queue verification email for new user_id=%s",
                user.id,
            )

            # The account and hashed token are already stored.
            # A resend-verification flow is needed to recover from this case.

        return user

    async def update_profile(
    self,
    user: User,
    payload: UserProfileUpdate,
    ) -> User:
        user.full_name = payload.full_name

        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(user)

        return user